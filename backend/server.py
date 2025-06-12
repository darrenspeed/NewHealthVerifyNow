from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, Depends, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import httpx
import csv
import io
import asyncio
from enum import Enum
import aiofiles
import hashlib
import sys
import pandas as pd
from datetime import datetime, timedelta
import schedule
import threading
import time

# Add current directory to Python path
sys.path.append(str(Path(__file__).parent))

# Import authentication and payment modules
from auth_models import (
    User, UserCreate, UserLogin, UserResponse, Token,
    Subscription, SubscriptionCreate, SubscriptionUpdate,
    PayPalCreateOrder, PayPalOrderResponse, PayPalCaptureOrder
)
from auth_utils import (
    verify_password, get_password_hash, create_access_token, verify_token,
    calculate_monthly_cost, get_pricing_tiers
)
from paypal_integration import paypal_client

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Health Verify Now API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current authenticated user"""
    email = verify_token(credentials.credentials)
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_data = await db.users.find_one({"email": email})
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return User(**user_data)

# Optional authentication (for public endpoints that can work with or without auth)
async def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[User]:
    """Get current user if authenticated, None otherwise"""
    if credentials is None:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None

# Enums
class VerificationStatus(str, Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"

class VerificationType(str, Enum):
    OIG = "oig"
    SAM = "sam"
    NSOPW = "nsopw"  # National Sex Offender Public Website
    LICENSE = "license"
    CRIMINAL = "criminal"

# Models
class Employee(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str  # Links employee to user account
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    ssn: str
    date_of_birth: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    license_number: Optional[str] = None
    license_type: Optional[str] = None
    license_state: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class EmployeeCreate(BaseModel):
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    ssn: str
    date_of_birth: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    license_number: Optional[str] = None
    license_type: Optional[str] = None
    license_state: Optional[str] = None

class VerificationResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    verification_type: VerificationType
    status: VerificationStatus
    results: Dict[str, Any] = {}
    error_message: Optional[str] = None
    checked_at: datetime = Field(default_factory=datetime.utcnow)
    data_source: Optional[str] = None

class BatchUploadResult(BaseModel):
    upload_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    filename: str
    total_rows: int
    successful_imports: int
    failed_imports: int
    errors: List[Dict[str, Any]] = []
    status: str  # processing, completed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

class BatchUploadStatus(BaseModel):
    upload_id: str
    status: str
    progress: int  # percentage
    total_rows: int
    processed_rows: int
    successful_imports: int
    failed_imports: int
    errors: List[Dict[str, Any]] = []

class BatchVerificationRequest(BaseModel):
    employee_ids: List[str]
    verification_types: List[VerificationType]

# OIG Exclusion Check Functions
OIG_DATA_FILE = ROOT_DIR / "oig_exclusions.csv"
OIG_DOWNLOAD_URL = "https://oig.hhs.gov/exclusions/downloadables/UPDATED.csv"

# SAM Exclusion Check Functions
SAM_DATA_FILE = ROOT_DIR / "sam_exclusions.csv"

async def download_oig_data():
    """Download the latest OIG exclusion list from HHS.gov"""
    try:
        logger.info("Downloading OIG exclusion data from HHS.gov...")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(OIG_DOWNLOAD_URL)
            
            if response.status_code == 200:
                # Save the data to local file
                async with aiofiles.open(OIG_DATA_FILE, 'wb') as f:
                    await f.write(response.content)
                
                logger.info(f"OIG data downloaded successfully: {len(response.content)} bytes")
                
                # Load data into memory for faster searches
                await load_oig_data_to_memory()
                return True
            else:
                logger.error(f"Failed to download OIG data: HTTP {response.status_code}")
                return False
                
    except Exception as e:
        logger.error(f"Error downloading OIG data: {e}")
        return False

async def download_sam_data():
    """Download the latest SAM exclusion data using the bulk download API"""
    try:
        sam_api_key = os.environ.get('SAM_API_KEY')
        if not sam_api_key:
            logger.error("SAM API key not configured for bulk download")
            return False
        
        logger.info("Initiating SAM bulk exclusion data download...")
        
        # Step 1: Request bulk download from SAM API V4
        base_url = "https://api.sam.gov/entity-information/v4/exclusions"
        params = {
            "api_key": sam_api_key,
            "classification": "Individual",  # Only get individuals
            "isActive": "Y",  # Only active exclusions
            "format": "csv"  # Request CSV format for easier parsing
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Request the bulk download
            response = await client.get(base_url, params=params)
            
            if response.status_code == 200:
                # SAM API V4 returns download instructions
                response_text = response.text
                
                if "Extract File will be available for download" in response_text:
                    # Extract the download URL from the response
                    import re
                    url_match = re.search(r'https://api\.sam\.gov/entity-information/v4/download-exclusions\?[^\\s]+', response_text)
                    
                    if url_match:
                        download_url = url_match.group(0)
                        # Replace the placeholder API key with actual key
                        download_url = download_url.replace("REPLACE_WITH_API_KEY", sam_api_key)
                        
                        logger.info(f"SAM download URL obtained: {download_url[:100]}...")
                        
                        # Step 2: Wait a bit for file preparation (SAM usually takes 30-60 seconds)
                        logger.info("Waiting for SAM file preparation (60 seconds)...")
                        await asyncio.sleep(60)
                        
                        # Step 3: Download the actual data file
                        logger.info("Downloading SAM exclusion data file...")
                        download_response = await client.get(download_url, timeout=300.0)
                        
                        if download_response.status_code == 200:
                            # Save the SAM data to local file
                            async with aiofiles.open(SAM_DATA_FILE, 'wb') as f:
                                await f.write(download_response.content)
                            
                            logger.info(f"SAM data downloaded successfully: {len(download_response.content)} bytes")
                            
                            # Load data into memory for faster searches
                            await load_sam_data_to_memory()
                            return True
                        else:
                            logger.error(f"Failed to download SAM data file: HTTP {download_response.status_code}")
                            return False
                    else:
                        logger.error("Could not extract download URL from SAM API response")
                        return False
                else:
                    logger.error("Unexpected response format from SAM API")
                    return False
            else:
                logger.error(f"Failed to request SAM bulk download: HTTP {response.status_code}")
                logger.error(f"Response: {response.text[:500]}")
                return False
                
    except Exception as e:
        logger.error(f"Error downloading SAM data: {e}")
        return False

async def load_sam_data_to_memory():
    """Load SAM exclusion data into memory for fast searches"""
    global sam_exclusions_cache
    
    if not SAM_DATA_FILE.exists():
        logger.warning("SAM data file not found, attempting to download...")
        if not await download_sam_data():
            return False
    
    try:
        logger.info("Loading SAM exclusion data into memory...")
        exclusions = []
        
        async with aiofiles.open(SAM_DATA_FILE, mode='r', encoding='utf-8') as f:
            content = await f.read()
            
        # Parse CSV content - SAM format may be different from OIG
        csv_reader = csv.DictReader(io.StringIO(content))
        
        for row in csv_reader:
            # Normalize SAM data format (fields may vary)
            exclusion = {
                'exclusion_name': row.get('exclusionName', '').strip().upper(),
                'first_name': row.get('firstName', '').strip().upper(),
                'last_name': row.get('lastName', '').strip().upper(),
                'middle_name': row.get('middleName', '').strip().upper(),
                'exclusion_type': row.get('exclusionType', '').strip(),
                'exclusion_program': row.get('exclusionProgram', '').strip(),
                'excluding_agency': row.get('excludingAgencyName', '').strip(),
                'activation_date': row.get('activationDate', '').strip(),
                'termination_date': row.get('terminationDate', '').strip(),
                'sam_number': row.get('samNumber', '').strip(),
                'cage_code': row.get('cageCode', '').strip(),
                'classification': row.get('classification', '').strip(),
                'address_line1': row.get('addressLine1', '').strip(),
                'city': row.get('city', '').strip(),
                'state_province': row.get('stateProvince', '').strip(),
                'zip_code': row.get('zipCode', '').strip(),
                'country': row.get('country', '').strip()
            }
            
            # Only include individuals (filter out companies)
            if exclusion['classification'].upper() in ['INDIVIDUAL', 'PERSON', '']:
                exclusions.append(exclusion)
        
        sam_exclusions_cache = exclusions
        logger.info(f"Loaded {len(exclusions)} SAM exclusions into memory")
        return True
        
    except Exception as e:
        logger.error(f"Error loading SAM data: {e}")
        return False

def search_sam_exclusions(first_name, last_name, middle_name=None):
    """Search SAM exclusions for matching individuals"""
    matches = []
    
    if not sam_exclusions_cache:
        logger.warning("SAM data not loaded in memory")
        return matches
    
    # Normalize search terms
    search_first = normalize_name(first_name)
    search_last = normalize_name(last_name)
    search_middle = normalize_name(middle_name) if middle_name else ""
    
    for exclusion in sam_exclusions_cache:
        match_score = 0
        
        # Method 1: Check individual name fields if available
        if exclusion['first_name'] and exclusion['last_name']:
            if (exclusion['first_name'] == search_first and 
                exclusion['last_name'] == search_last):
                
                match_score = 100  # Exact first + last name match
                
                # Check middle name if provided
                if search_middle and exclusion['middle_name']:
                    if exclusion['middle_name'] == search_middle:
                        match_score = 100  # Perfect match
                    elif exclusion['middle_name'].startswith(search_middle) or search_middle.startswith(exclusion['middle_name']):
                        match_score = 95   # Partial middle name match
                    else:
                        match_score = 85   # Different middle name
        
        # Method 2: Check full name field (exclusion_name)
        elif exclusion['exclusion_name']:
            full_search_name = f"{search_first} {search_last}"
            full_search_name_with_middle = f"{search_first} {search_middle} {search_last}" if search_middle else full_search_name
            
            # Check if our search name is in the exclusion name
            if full_search_name in exclusion['exclusion_name']:
                match_score = 90
            elif search_middle and full_search_name_with_middle in exclusion['exclusion_name']:
                match_score = 95
            elif (search_first in exclusion['exclusion_name'] and 
                  search_last in exclusion['exclusion_name']):
                match_score = 80
        
        # Only include high-confidence matches
        if match_score >= 80:
            matches.append({
                'exclusion': exclusion,
                'match_score': match_score,
                'match_type': 'name_match'
            })
    
    # Sort by match score (highest first)
    matches.sort(key=lambda x: x['match_score'], reverse=True)
    
    return matches

# In-memory OIG data storage for fast searches
oig_exclusions_cache = []

# In-memory SAM data storage for fast searches
sam_exclusions_cache = []

async def load_oig_data_to_memory():
    """Load OIG exclusion data into memory for fast searches"""
    global oig_exclusions_cache
    
    if not OIG_DATA_FILE.exists():
        logger.warning("OIG data file not found, attempting to download...")
        if not await download_oig_data():
            return False
    
    try:
        logger.info("Loading OIG exclusion data into memory...")
        exclusions = []
        
        async with aiofiles.open(OIG_DATA_FILE, mode='r', encoding='utf-8') as f:
            content = await f.read()
            
        # Parse CSV content
        csv_reader = csv.DictReader(io.StringIO(content))
        
        for row in csv_reader:
            # Clean and normalize data
            exclusion = {
                'lastname': row.get('LASTNAME', '').strip().upper(),
                'firstname': row.get('FIRSTNAME', '').strip().upper(),
                'midname': row.get('MIDNAME', '').strip().upper(),
                'busname': row.get('BUSNAME', '').strip().upper(),
                'general': row.get('GENERAL', '').strip(),
                'specialty': row.get('SPECIALTY', '').strip(),
                'upin': row.get('UPIN', '').strip(),
                'npi': row.get('NPI', '').strip(),
                'dob': row.get('DOB', '').strip(),
                'address': row.get('ADDRESS', '').strip(),
                'city': row.get('CITY', '').strip(),
                'state': row.get('STATE', '').strip(),
                'zip': row.get('ZIP', '').strip(),
                'excltype': row.get('EXCLTYPE', '').strip(),
                'excldate': row.get('EXCLDATE', '').strip(),
                'reindate': row.get('REINDATE', '').strip(),
                'waiverdate': row.get('WAIVERDATE', '').strip(),
                'wvrstate': row.get('WVRSTATE', '').strip()
            }
            exclusions.append(exclusion)
        
        oig_exclusions_cache = exclusions
        logger.info(f"Loaded {len(exclusions)} OIG exclusions into memory")
        return True
        
    except Exception as e:
        logger.error(f"Error loading OIG data: {e}")
        return False

def normalize_name(name):
    """Normalize a name for comparison"""
    if not name:
        return ""
    return name.strip().upper().replace('.', '').replace(',', '').replace('-', ' ')

def search_oig_exclusions(first_name, last_name, middle_name=None):
    """Search OIG exclusions for matching individuals"""
    matches = []
    
    if not oig_exclusions_cache:
        logger.warning("OIG data not loaded in memory")
        return matches
    
    # Normalize search terms
    search_first = normalize_name(first_name)
    search_last = normalize_name(last_name)
    search_middle = normalize_name(middle_name) if middle_name else ""
    
    for exclusion in oig_exclusions_cache:
        # Check for exact matches on first and last name
        if (exclusion['firstname'] == search_first and 
            exclusion['lastname'] == search_last):
            
            match_score = 100  # Exact first + last name match
            
            # Check middle name if provided
            if search_middle and exclusion['midname']:
                if exclusion['midname'] == search_middle:
                    match_score = 100  # Perfect match
                elif exclusion['midname'].startswith(search_middle) or search_middle.startswith(exclusion['midname']):
                    match_score = 95   # Partial middle name match
                else:
                    match_score = 85   # Different middle name
            
            matches.append({
                'exclusion': exclusion,
                'match_score': match_score,
                'match_type': 'exact_name'
            })
    
    # Sort by match score (highest first)
    matches.sort(key=lambda x: x['match_score'], reverse=True)
    
    return matches

async def check_oig_exclusion(employee: Employee) -> VerificationResult:
    """Check if employee is in OIG exclusion list using real HHS data"""
    try:
        # Ensure OIG data is loaded
        if not oig_exclusions_cache:
            logger.info("OIG data not in memory, loading...")
            await load_oig_data_to_memory()
        
        if not oig_exclusions_cache:
            logger.error("Failed to load OIG exclusion data")
            result = VerificationResult(
                employee_id=employee.id,
                verification_type=VerificationType.OIG,
                status=VerificationStatus.ERROR,
                error_message="OIG exclusion database not available",
                data_source="OIG LEIE Database"
            )
            await db.verification_results.insert_one(result.dict())
            return result
        
        # Search for matches
        matches = search_oig_exclusions(
            employee.first_name, 
            employee.last_name, 
            employee.middle_name
        )
        
        is_excluded = len(matches) > 0
        
        # Prepare match details for high-confidence matches
        high_confidence_matches = [m for m in matches if m['match_score'] >= 90]
        
        result = VerificationResult(
            employee_id=employee.id,
            verification_type=VerificationType.OIG,
            status=VerificationStatus.FAILED if len(high_confidence_matches) > 0 else VerificationStatus.PASSED,
            results={
                "excluded": len(high_confidence_matches) > 0,
                "total_matches_found": len(matches),
                "high_confidence_matches": len(high_confidence_matches),
                "match_details": [
                    {
                        "name": f"{match['exclusion']['firstname']} {match['exclusion']['midname']} {match['exclusion']['lastname']}".strip(),
                        "business_name": match['exclusion']['busname'],
                        "exclusion_type": match['exclusion']['excltype'],
                        "exclusion_date": match['exclusion']['excldate'],
                        "address": f"{match['exclusion']['address']}, {match['exclusion']['city']}, {match['exclusion']['state']} {match['exclusion']['zip']}".strip().rstrip(','),
                        "specialty": match['exclusion']['specialty'],
                        "npi": match['exclusion']['npi'],
                        "match_score": match['match_score']
                    }
                    for match in high_confidence_matches[:5]  # Limit to top 5 matches
                ],
                "search_criteria": {
                    "first_name": employee.first_name,
                    "last_name": employee.last_name,
                    "middle_name": employee.middle_name,
                    "ssn_last_4": employee.ssn[-4:] if len(employee.ssn) >= 4 else "N/A"
                },
                "database_info": {
                    "total_exclusions_in_database": len(oig_exclusions_cache),
                    "last_updated": datetime.utcnow().isoformat(),
                    "source": "HHS OIG LEIE Database"
                }
            },
            data_source="OIG LEIE Database"
        )
        
        # Store result in database
        await db.verification_results.insert_one(result.dict())
        
        logger.info(f"OIG check completed for {employee.first_name} {employee.last_name}: {result.status} ({len(high_confidence_matches)} high-confidence matches)")
        
        return result
        
    except Exception as e:
        logger.error(f"Error checking OIG exclusion for employee {employee.id}: {e}")
        error_result = VerificationResult(
            employee_id=employee.id,
            verification_type=VerificationType.OIG,
            status=VerificationStatus.ERROR,
            error_message=str(e),
            data_source="OIG LEIE Database"
        )
        await db.verification_results.insert_one(error_result.dict())
        return error_result

async def check_sam_exclusion(employee: Employee) -> VerificationResult:
    """Check if employee is in SAM exclusion list using downloaded SAM data
    
    This function now uses locally downloaded SAM data for real-time searches,
    similar to how OIG verification works.
    """
    try:
        # Ensure SAM data is loaded
        if not sam_exclusions_cache:
            logger.info("SAM data not in memory, loading...")
            await load_sam_data_to_memory()
        
        if not sam_exclusions_cache:
            logger.error("Failed to load SAM exclusion data")
            result = VerificationResult(
                employee_id=employee.id,
                verification_type=VerificationType.SAM,
                status=VerificationStatus.ERROR,
                error_message="SAM exclusion database not available",
                data_source="SAM.gov Bulk Data"
            )
            await db.verification_results.insert_one(result.dict())
            return result
        
        # Search for matches using local data
        matches = search_sam_exclusions(
            employee.first_name, 
            employee.last_name, 
            employee.middle_name
        )
        
        # Prepare match details for high-confidence matches
        high_confidence_matches = [m for m in matches if m['match_score'] >= 90]
        
        result = VerificationResult(
            employee_id=employee.id,
            verification_type=VerificationType.SAM,
            status=VerificationStatus.FAILED if len(high_confidence_matches) > 0 else VerificationStatus.PASSED,
            results={
                "excluded": len(high_confidence_matches) > 0,
                "total_matches_found": len(matches),
                "high_confidence_matches": len(high_confidence_matches),
                "match_details": [
                    {
                        "exclusion_name": match['exclusion']['exclusion_name'] or f"{match['exclusion']['first_name']} {match['exclusion']['last_name']}".strip(),
                        "exclusion_type": match['exclusion']['exclusion_type'],
                        "exclusion_program": match['exclusion']['exclusion_program'],
                        "excluding_agency": match['exclusion']['excluding_agency'],
                        "activation_date": match['exclusion']['activation_date'],
                        "termination_date": match['exclusion']['termination_date'],
                        "sam_number": match['exclusion']['sam_number'],
                        "cage_code": match['exclusion']['cage_code'],
                        "classification": match['exclusion']['classification'],
                        "address": f"{match['exclusion']['address_line1']}, {match['exclusion']['city']}, {match['exclusion']['state_province']} {match['exclusion']['zip_code']} {match['exclusion']['country']}".strip().rstrip(','),
                        "match_score": match['match_score']
                    }
                    for match in high_confidence_matches[:5]  # Limit to top 5 matches
                ],
                "search_criteria": {
                    "first_name": employee.first_name,
                    "last_name": employee.last_name,
                    "middle_name": employee.middle_name,
                    "ssn_last_4": employee.ssn[-4:] if len(employee.ssn) >= 4 else "N/A"
                },
                "database_info": {
                    "total_exclusions_in_database": len(sam_exclusions_cache),
                    "last_updated": datetime.utcnow().isoformat(),
                    "source": "SAM.gov Bulk Data Download",
                    "verification_method": "Local Search"
                }
            },
            data_source="SAM.gov Bulk Data"
        )
        
        # Store result in database
        await db.verification_results.insert_one(result.dict())
        
        logger.info(f"SAM check completed for {employee.first_name} {employee.last_name}: {result.status} ({len(high_confidence_matches)} high-confidence matches)")
        
        return result
        
    except Exception as e:
        logger.error(f"Error checking SAM exclusion for employee {employee.id}: {e}")
        error_result = VerificationResult(
            employee_id=employee.id,
            verification_type=VerificationType.SAM,
            status=VerificationStatus.ERROR,
            error_message=str(e),
            data_source="SAM.gov Bulk Data"
        )
        await db.verification_results.insert_one(error_result.dict())
        return error_result
        
    except httpx.TimeoutException:
        logger.error(f"SAM API timeout for employee {employee.id}")
        error_result = VerificationResult(
            employee_id=employee.id,
            verification_type=VerificationType.SAM,
            status=VerificationStatus.ERROR,
            error_message="SAM API request timed out",
            data_source="SAM.gov API"
        )
        await db.verification_results.insert_one(error_result.dict())
        return error_result
        
    except Exception as e:
        logger.error(f"Error checking SAM exclusion for employee {employee.id}: {e}")
        error_result = VerificationResult(
            employee_id=employee.id,
            verification_type=VerificationType.SAM,
            status=VerificationStatus.ERROR,
            error_message=str(e),
            data_source="SAM.gov API"
        )
        await db.verification_results.insert_one(error_result.dict())
        return error_result

# API Routes

# ========== PUBLIC ROUTES (No Authentication Required) ==========

@api_router.get("/")
async def root():
    return {"message": "Health Verify Now API", "version": "1.0.0", "status": "active"}

@api_router.get("/test-sam")
async def test_sam_api():
    """Test SAM bulk data download and local search capability"""
    try:
        sam_api_key = os.environ.get('SAM_API_KEY')
        if not sam_api_key:
            return {"error": "SAM API key not configured"}
        
        # Check current status of both databases
        oig_loaded = len(oig_exclusions_cache) > 0
        sam_loaded = len(sam_exclusions_cache) > 0
        
        return {
            "verification_system_status": {
                "oig_database": {
                    "loaded": oig_loaded,
                    "exclusions_count": len(oig_exclusions_cache),
                    "source": "HHS OIG LEIE Database",
                    "method": "Downloaded CSV, Local Search"
                },
                "sam_database": {
                    "loaded": sam_loaded,
                    "exclusions_count": len(sam_exclusions_cache),
                    "source": "SAM.gov Bulk Data",
                    "method": "Bulk Download, Local Search"
                }
            },
            "sam_api_info": {
                "api_key_configured": bool(sam_api_key),
                "api_key_partial": f"{sam_api_key[:8]}...{sam_api_key[-4:]}" if sam_api_key else None,
                "bulk_download_capability": "Available",
                "real_time_search": "Local Database" if sam_loaded else "Not Available"
            },
            "system_capabilities": {
                "oig_verification": "✅ Real-time local search" if oig_loaded else "❌ Database not loaded",
                "sam_verification": "✅ Real-time local search" if sam_loaded else "❌ Database not loaded",
                "batch_verification": "✅ Both OIG and SAM" if (oig_loaded and sam_loaded) else "⚠️ Partial capability"
            },
            "recommendations": {
                "for_production": "Both databases should be loaded for comprehensive verification",
                "data_freshness": "Consider implementing daily/weekly database updates",
                "performance": "Local search provides instant results without API rate limits"
            }
        }
    except Exception as e:
        return {"error": str(e), "error_type": type(e).__name__}

@api_router.get("/admin/sam-status")
async def check_sam_status():
    """Admin endpoint to check SAM API status and attempt manual download"""
    try:
        sam_api_key = os.environ.get('SAM_API_KEY')
        if not sam_api_key:
            return {"error": "SAM API key not configured"}
        
        # Check current local status
        local_status = {
            "sam_loaded": len(sam_exclusions_cache) > 0,
            "exclusions_count": len(sam_exclusions_cache),
            "last_successful_download": None  # Could store this in database
        }
        
        # Test SAM API connectivity
        base_url = "https://api.sam.gov/entity-information/v4/exclusions"
        params = {
            "api_key": sam_api_key,
            "classification": "Individual",
            "isActive": "Y",
            "format": "csv"
        }
        
        api_status = {}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(base_url, params=params)
                
                api_status = {
                    "api_available": response.status_code == 200,
                    "status_code": response.status_code,
                    "response_indicates_download": "Extract File will be available" in response.text,
                    "last_checked": datetime.utcnow().isoformat()
                }
                
                # If API is working, extract download URL
                if response.status_code == 200 and "Extract File will be available" in response.text:
                    import re
                    url_match = re.search(r'https://api\.sam\.gov/entity-information/v4/download-exclusions\?[^\\s]+', response.text)
                    if url_match:
                        api_status["download_url_available"] = True
                        api_status["estimated_file_ready_time"] = (datetime.utcnow() + timedelta(seconds=60)).isoformat()
                    else:
                        api_status["download_url_available"] = False
                
            except Exception as e:
                api_status = {
                    "api_available": False,
                    "error": str(e),
                    "last_checked": datetime.utcnow().isoformat()
                }
        
        return {
            "local_database": local_status,
            "sam_api_status": api_status,
            "recommendations": {
                "if_api_working": "Call /admin/download-sam to manually trigger download",
                "monitoring": "Check this endpoint periodically to monitor API status",
                "automation": "Consider implementing scheduled checks"
            }
        }
        
    except Exception as e:
        return {"error": str(e), "error_type": type(e).__name__}

@api_router.post("/admin/download-sam")
async def manual_sam_download():
    """Admin endpoint to manually trigger SAM data download"""
    try:
        # Attempt to download SAM data
        success = await download_sam_data()
        
        return {
            "download_attempted": True,
            "success": success,
            "sam_loaded": len(sam_exclusions_cache) > 0,
            "exclusions_count": len(sam_exclusions_cache),
            "timestamp": datetime.utcnow().isoformat(),
            "message": "SAM data downloaded successfully" if success else "SAM download failed - check logs for details"
        }
        
    except Exception as e:
        logger.error(f"Manual SAM download failed: {e}")
        return {
            "download_attempted": True,
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# ========== AUTHENTICATION ROUTES ==========

@api_router.post("/auth/register", response_model=Token)
async def register(user_data: UserCreate):
    """Register a new user"""
    try:
        # Check if user already exists
        existing_user = await db.users.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash password and create user
        hashed_password = get_password_hash(user_data.password)
        user_dict = user_data.dict()
        del user_dict['password']
        
        user = User(**user_dict)
        user_doc = user.dict()
        user_doc['hashed_password'] = hashed_password
        
        await db.users.insert_one(user_doc)
        
        # Create access token
        access_token = create_access_token(data={"sub": user.email})
        
        logger.info(f"New user registered: {user.email}")
        
        return Token(
            access_token=access_token,
            user=UserResponse(**user.dict())
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@api_router.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin):
    """Login user"""
    try:
        # Find user
        user_doc = await db.users.find_one({"email": user_data.email})
        if not user_doc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not verify_password(user_data.password, user_doc['hashed_password']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if user is active
        if not user_doc.get('is_active', True):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated"
            )
        
        # Create access token
        access_token = create_access_token(data={"sub": user_doc['email']})
        
        user = User(**user_doc)
        
        logger.info(f"User logged in: {user.email}")
        
        return Token(
            access_token=access_token,
            user=UserResponse(**user.dict())
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@api_router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(**current_user.dict())

# ========== PAYMENT ROUTES ==========

@api_router.post("/payment/create-subscription")
async def create_subscription(
    subscription_data: SubscriptionCreate,
    current_user: User = Depends(get_current_user)
):
    """Create PayPal subscription for user"""
    try:
        # Calculate pricing
        plan_name, monthly_cost = calculate_monthly_cost(subscription_data.employee_count)
        
        # Check if user already has an active subscription
        existing_subscription = await db.subscriptions.find_one({
            "user_id": current_user.id,
            "status": "active"
        })
        
        if existing_subscription:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already has an active subscription"
            )
        
        try:
            # Get PayPal configuration
            paypal_business_email = os.environ.get('PAYPAL_BUSINESS_EMAIL')
            is_sandbox = os.environ.get('PAYPAL_MODE', 'sandbox').lower() == 'sandbox'
            
            # Validate business email exists
            if not paypal_business_email:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="PayPal business email not configured"
                )
            
            # Calculate total monthly cost
            total_monthly_cost = monthly_cost
            
            # Generate a unique payment reference
            payment_reference = f"HVN-{current_user.id[:8]}-{subscription_data.employee_count}-{datetime.utcnow().strftime('%Y%m%d')}"
            
            # Use appropriate PayPal URL (sandbox vs production)
            if is_sandbox:
                paypal_base_url = "https://www.sandbox.paypal.com/cgi-bin/webscr"
            else:
                paypal_base_url = "https://www.paypal.com/cgi-bin/webscr"
            
            # Create PayPal payment URL for recurring payments
            paypal_payment_url = (
                f"{paypal_base_url}?"
                f"cmd=_xclick-subscriptions&"
                f"business={paypal_business_email}&"
                f"item_name=Health Verify Now - {plan_name} Plan ({subscription_data.employee_count} employees)&"
                f"currency_code=USD&"
                f"a3={total_monthly_cost:.2f}&"  # Subscription amount
                f"p3=1&"  # Billing cycle
                f"t3=M&"  # Billing cycle unit (M = month)
                f"src=1&"  # Recurring payments
                f"sra=1&"  # Re-attempt on failure
                f"custom={payment_reference}&"
                f"return=https://www.healthverifynow.com/payment/success&"
                f"cancel_return=https://www.healthverifynow.com/payment/cancel&"
                f"notify_url=https://www.healthverifynow.com/api/paypal/ipn"
            )
            
            # Create subscription record as "pending_payment"
            subscription_id = str(uuid.uuid4())
            
            paypal_subscription = {
                'subscription_id': subscription_id,
                'approval_url': paypal_payment_url,
                'status': 'pending_payment',
                'payment_reference': payment_reference
            }
            
            logger.info(f"Created PayPal subscription link for customer: {current_user.email}")
            logger.info(f"Amount: ${total_monthly_cost}, Plan: {plan_name}, Reference: {payment_reference}")
            logger.info(f"Using PayPal business email: {paypal_business_email}")
            logger.info(f"Sandbox mode: {is_sandbox}")
            
        except Exception as e:
            logger.error(f"Error creating PayPal payment link: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Payment link creation failed"
            )
        
        # Save subscription to database
        subscription = Subscription(
            user_id=current_user.id,
            paypal_subscription_id=paypal_subscription['subscription_id'],
            plan_name=plan_name,
            employee_count=subscription_data.employee_count,
            monthly_cost=monthly_cost,
            status=paypal_subscription['status'],
            next_billing_date=datetime.utcnow() + timedelta(days=30)
        )
        
        await db.subscriptions.insert_one(subscription.dict())
        
        # Update user with subscription info
        await db.users.update_one(
            {"id": current_user.id},
            {
                "$set": {
                    "paypal_subscription_id": paypal_subscription['subscription_id'],
                    "current_plan": plan_name,
                    "employee_count": subscription_data.employee_count,
                    "monthly_cost": monthly_cost,
                    "next_billing_date": subscription.next_billing_date,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        logger.info(f"Subscription created for user {current_user.email}: {plan_name}, {subscription_data.employee_count} employees, ${monthly_cost}/month")
        
        return {
            "subscription_id": subscription.id,
            "paypal_subscription_id": paypal_subscription['subscription_id'],
            "approval_url": paypal_subscription['approval_url'],
            "plan_name": plan_name,
            "employee_count": subscription_data.employee_count,
            "monthly_cost": monthly_cost,
            "status": paypal_subscription['status']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subscription"
        )

@api_router.get("/payment/subscription")
async def get_user_subscription(current_user: User = Depends(get_current_user)):
    """Get user's current subscription"""
    try:
        subscription = await db.subscriptions.find_one({
            "user_id": current_user.id,
            "status": {"$in": ["active", "pending", "APPROVAL_PENDING", "pending_payment"]}
        })
        
        if not subscription:
            return {"subscription": None}
        
        # Get latest PayPal subscription status
        try:
            paypal_sub = await paypal_client.get_subscription(subscription['paypal_subscription_id'])
            if paypal_sub:
                # Update local status if different
                if paypal_sub.get('status') != subscription['status']:
                    await db.subscriptions.update_one(
                        {"id": subscription['id']},
                        {"$set": {"status": paypal_sub.get('status'), "updated_at": datetime.utcnow()}}
                    )
                    subscription['status'] = paypal_sub.get('status')
        except Exception as e:
            logger.warning(f"Could not get PayPal subscription status: {e}")
        
        return {
            "subscription": Subscription(**subscription)
        }
        
    except Exception as e:
        logger.error(f"Error getting user subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get subscription"
        )

@api_router.patch("/payment/subscription")
async def update_subscription(
    subscription_update: SubscriptionUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update user's subscription (change employee count)"""
    try:
        # Get current subscription
        subscription = await db.subscriptions.find_one({
            "user_id": current_user.id,
            "status": "active"
        })
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found"
            )
        
        # Calculate new pricing
        new_plan_name, new_monthly_cost = calculate_monthly_cost(subscription_update.employee_count)
        
        # Update PayPal subscription quantity
        success = await paypal_client.update_subscription_quantity(
            subscription['paypal_subscription_id'],
            subscription_update.employee_count
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update PayPal subscription"
            )
        
        # Update local subscription
        await db.subscriptions.update_one(
            {"id": subscription['id']},
            {
                "$set": {
                    "employee_count": subscription_update.employee_count,
                    "monthly_cost": new_monthly_cost,
                    "plan_name": new_plan_name,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Update user
        await db.users.update_one(
            {"id": current_user.id},
            {
                "$set": {
                    "employee_count": subscription_update.employee_count,
                    "monthly_cost": new_monthly_cost,
                    "current_plan": new_plan_name,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        logger.info(f"Subscription updated for user {current_user.email}: {new_plan_name}, {subscription_update.employee_count} employees, ${new_monthly_cost}/month")
        
        return {
            "plan_name": new_plan_name,
            "employee_count": subscription_update.employee_count,
            "monthly_cost": new_monthly_cost,
            "message": "Subscription updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update subscription"
        )

@api_router.delete("/payment/subscription")
async def cancel_subscription(current_user: User = Depends(get_current_user)):
    """Cancel user's subscription"""
    try:
        # Get current subscription
        subscription = await db.subscriptions.find_one({
            "user_id": current_user.id,
            "status": "active"
        })
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found"
            )
        
        # Cancel PayPal subscription
        success = await paypal_client.cancel_subscription(
            subscription['paypal_subscription_id'],
            "Customer requested cancellation"
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cancel PayPal subscription"
            )
        
        # Update local subscription status
        await db.subscriptions.update_one(
            {"id": subscription['id']},
            {
                "$set": {
                    "status": "cancelled",
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Update user
        await db.users.update_one(
            {"id": current_user.id},
            {
                "$set": {
                    "current_plan": None,
                    "employee_count": 0,
                    "monthly_cost": 0.0,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        logger.info(f"Subscription cancelled for user {current_user.email}")
        
        return {"message": "Subscription cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription"
        )

# ========== BATCH UPLOAD ROUTES (Authenticated) ==========

@api_router.post("/employees/batch-upload")
async def upload_employees_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Upload CSV file with employee data for batch processing"""
    try:
        # Validate file type
        if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be CSV, Excel (.xlsx), or Excel (.xls) format"
            )
        
        # Check file size (limit to 10MB)
        file_content = await file.read()
        if len(file_content) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size must be less than 10MB"
            )
        
        # Create upload record
        upload_id = str(uuid.uuid4())
        upload_record = {
            "upload_id": upload_id,
            "user_id": current_user.id,
            "filename": file.filename,
            "total_rows": 0,
            "successful_imports": 0,
            "failed_imports": 0,
            "errors": [],
            "status": "processing",
            "created_at": datetime.utcnow(),
            "completed_at": None
        }
        
        await db.batch_uploads.insert_one(upload_record)
        
        # Start background processing
        background_tasks.add_task(
            process_employee_csv,
            upload_id,
            file_content,
            file.filename,
            current_user.id
        )
        
        logger.info(f"Started batch upload processing for user {current_user.email}: {file.filename}")
        
        return {
            "upload_id": upload_id,
            "message": "File upload started. Processing in background.",
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting batch upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start batch upload"
        )

@api_router.get("/employees/batch-upload/{upload_id}/status")
async def get_batch_upload_status(
    upload_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get status of batch upload processing"""
    try:
        upload_record = await db.batch_uploads.find_one({
            "upload_id": upload_id,
            "user_id": current_user.id
        })
        
        if not upload_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload not found"
            )
        
        # Calculate progress percentage
        progress = 0
        if upload_record["total_rows"] > 0:
            processed = upload_record["successful_imports"] + upload_record["failed_imports"]
            progress = int((processed / upload_record["total_rows"]) * 100)
        
        return BatchUploadStatus(
            upload_id=upload_id,
            status=upload_record["status"],
            progress=progress,
            total_rows=upload_record["total_rows"],
            processed_rows=upload_record["successful_imports"] + upload_record["failed_imports"],
            successful_imports=upload_record["successful_imports"],
            failed_imports=upload_record["failed_imports"],
            errors=upload_record["errors"][:10]  # Limit to first 10 errors
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch upload status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get upload status"
        )

@api_router.get("/employees/batch-uploads")
async def get_batch_upload_history(current_user: User = Depends(get_current_user)):
    """Get batch upload history for current user"""
    try:
        uploads = await db.batch_uploads.find({
            "user_id": current_user.id
        }).sort("created_at", -1).limit(50).to_list(50)
        
        return [BatchUploadResult(**upload) for upload in uploads]
        
    except Exception as e:
        logger.error(f"Error getting batch upload history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get upload history"
        )

async def process_employee_csv(upload_id: str, file_content: bytes, filename: str, user_id: str):
    """Background task to process CSV file and create employees"""
    try:
        logger.info(f"Starting CSV processing for upload {upload_id}")
        
        # Parse CSV/Excel file
        employees_data = []
        errors = []
        
        if filename.endswith('.csv'):
            # Parse CSV
            try:
                csv_content = file_content.decode('utf-8')
                csv_reader = csv.DictReader(io.StringIO(csv_content))
                employees_data = list(csv_reader)
            except UnicodeDecodeError:
                # Try different encoding
                csv_content = file_content.decode('latin-1')
                csv_reader = csv.DictReader(io.StringIO(csv_content))
                employees_data = list(csv_reader)
        else:
            # Parse Excel
            df = pd.read_excel(io.BytesIO(file_content))
            employees_data = df.to_dict('records')
        
        total_rows = len(employees_data)
        successful_imports = 0
        failed_imports = 0
        
        # Update total rows
        await db.batch_uploads.update_one(
            {"upload_id": upload_id},
            {"$set": {"total_rows": total_rows}}
        )
        
        logger.info(f"Processing {total_rows} rows for upload {upload_id}")
        
        # Process each employee
        for row_index, row_data in enumerate(employees_data):
            try:
                # Map CSV columns to employee fields (flexible column mapping)
                employee_data = map_csv_row_to_employee(row_data)
                
                # Validate required fields
                if not employee_data.get('first_name') or not employee_data.get('last_name'):
                    errors.append({
                        "row": row_index + 1,
                        "error": "Missing required fields: first_name and last_name",
                        "data": row_data
                    })
                    failed_imports += 1
                    continue
                
                # Add user_id and create employee
                employee_data['user_id'] = user_id
                employee = Employee(**employee_data)
                
                # Check if employee already exists (by name + SSN)
                existing = await db.employees.find_one({
                    "user_id": user_id,
                    "first_name": employee.first_name,
                    "last_name": employee.last_name,
                    "ssn": employee.ssn
                })
                
                if existing:
                    errors.append({
                        "row": row_index + 1,
                        "error": "Employee already exists",
                        "data": {"name": f"{employee.first_name} {employee.last_name}", "ssn": employee.ssn[-4:] if employee.ssn else "N/A"}
                    })
                    failed_imports += 1
                    continue
                
                # Insert employee
                await db.employees.insert_one(employee.dict())
                successful_imports += 1
                
                # Update progress every 10 employees
                if (row_index + 1) % 10 == 0:
                    await db.batch_uploads.update_one(
                        {"upload_id": upload_id},
                        {
                            "$set": {
                                "successful_imports": successful_imports,
                                "failed_imports": failed_imports,
                                "errors": errors[:100]  # Keep only first 100 errors
                            }
                        }
                    )
                
            except Exception as e:
                errors.append({
                    "row": row_index + 1,
                    "error": str(e),
                    "data": row_data
                })
                failed_imports += 1
                logger.warning(f"Error processing row {row_index + 1}: {e}")
        
        # Final update
        await db.batch_uploads.update_one(
            {"upload_id": upload_id},
            {
                "$set": {
                    "successful_imports": successful_imports,
                    "failed_imports": failed_imports,
                    "errors": errors[:100],
                    "status": "completed",
                    "completed_at": datetime.utcnow()
                }
            }
        )
        
        logger.info(f"Completed CSV processing for upload {upload_id}: {successful_imports} successful, {failed_imports} failed")
        
    except Exception as e:
        logger.error(f"Error in CSV processing for upload {upload_id}: {e}")
        await db.batch_uploads.update_one(
            {"upload_id": upload_id},
            {
                "$set": {
                    "status": "failed",
                    "errors": [{"error": f"Processing failed: {str(e)}"}],
                    "completed_at": datetime.utcnow()
                }
            }
        )

def map_csv_row_to_employee(row_data: Dict[str, Any]) -> Dict[str, Any]:
    """Map CSV row data to employee fields with flexible column naming"""
    
    # Define possible column name variations
    column_mappings = {
        'first_name': ['first_name', 'firstname', 'first name', 'fname', 'given_name'],
        'last_name': ['last_name', 'lastname', 'last name', 'lname', 'surname', 'family_name'],
        'middle_name': ['middle_name', 'middlename', 'middle name', 'mname', 'middle_initial'],
        'ssn': ['ssn', 'social_security_number', 'social security number', 'social_security', 'ss_number'],
        'date_of_birth': ['date_of_birth', 'dob', 'birth_date', 'birthdate', 'date of birth'],
        'email': ['email', 'email_address', 'email address', 'e_mail', 'work_email'],
        'phone': ['phone', 'phone_number', 'phone number', 'telephone', 'mobile', 'cell'],
        'license_number': ['license_number', 'license number', 'license_no', 'license', 'professional_license'],
        'license_type': ['license_type', 'license type', 'license_category', 'profession', 'credential'],
        'license_state': ['license_state', 'license state', 'state', 'license_jurisdiction']
    }
    
    employee_data = {}
    
    # Normalize column names (lowercase, strip spaces)
    normalized_row = {k.lower().strip(): v for k, v in row_data.items() if v is not None and str(v).strip()}
    
    # Map fields
    for field_name, possible_columns in column_mappings.items():
        for col_name in possible_columns:
            if col_name in normalized_row and str(normalized_row[col_name]).strip():
                employee_data[field_name] = str(normalized_row[col_name]).strip()
                break
    
    return employee_data

@api_router.post("/employees", response_model=Employee)
async def create_employee(
    employee_data: EmployeeCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new employee record"""
    try:
        # Check if user has active subscription and employee limit
        if current_user.employee_count > 0:
            current_employees = await db.employees.count_documents({"user_id": current_user.id})
            if current_employees >= current_user.employee_count:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"Employee limit reached. Current plan allows {current_user.employee_count} employees. Please upgrade your subscription."
                )
        
        employee_dict = employee_data.dict()
        employee_dict['user_id'] = current_user.id  # Associate with current user
        employee = Employee(**employee_dict)
        
        await db.employees.insert_one(employee.dict())
        
        logger.info(f"Created employee: {employee.first_name} {employee.last_name} for user {current_user.email}")
        return employee
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating employee: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@api_router.get("/employees", response_model=List[Employee])
async def get_employees(current_user: User = Depends(get_current_user)):
    """Get all employees for current user"""
    try:
        employees = await db.employees.find({"user_id": current_user.id}).to_list(1000)
        return [Employee(**emp) for emp in employees]
    except Exception as e:
        logger.error(f"Error fetching employees: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/employees/{employee_id}", response_model=Employee)
async def get_employee(employee_id: str, current_user: User = Depends(get_current_user)):
    """Get a specific employee"""
    try:
        employee = await db.employees.find_one({"id": employee_id, "user_id": current_user.id})
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        return Employee(**employee)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching employee {employee_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/employees/{employee_id}/verify")
async def verify_employee(
    employee_id: str, 
    verification_types: List[VerificationType],
    current_user: User = Depends(get_current_user)
):
    """Run verification checks for an employee"""
    try:
        # Check if user has active subscription
        if not current_user.current_plan:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Active subscription required to perform verifications"
            )
        
        # Get employee (ensure it belongs to current user)
        employee_data = await db.employees.find_one({"id": employee_id, "user_id": current_user.id})
        if not employee_data:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        employee = Employee(**employee_data)
        results = []
        
        for verification_type in verification_types:
            if verification_type == VerificationType.OIG:
                result = await check_oig_exclusion(employee)
                results.append(result)
            elif verification_type == VerificationType.SAM:
                result = await check_sam_exclusion(employee)
                results.append(result)
            else:
                # Placeholder for other verification types
                result = VerificationResult(
                    employee_id=employee_id,
                    verification_type=verification_type,
                    status=VerificationStatus.PENDING,
                    results={"message": f"{verification_type.value} verification not yet implemented"},
                    data_source=f"{verification_type.value.upper()} API"
                )
                await db.verification_results.insert_one(result.dict())
                results.append(result)
        
        return {"employee_id": employee_id, "results": results}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying employee {employee_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/employees/{employee_id}/verification-results")
async def get_employee_verification_results(
    employee_id: str, 
    current_user: User = Depends(get_current_user)
):
    """Get all verification results for an employee"""
    try:
        # Verify employee belongs to current user
        employee = await db.employees.find_one({"id": employee_id, "user_id": current_user.id})
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        results = await db.verification_results.find({"employee_id": employee_id}).to_list(1000)
        return [VerificationResult(**result) for result in results]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching verification results for employee {employee_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/verify-batch")
async def verify_batch(
    request: BatchVerificationRequest, 
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Run batch verification for multiple employees"""
    try:
        # Check if user has active subscription
        if not current_user.current_plan:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Active subscription required to perform verifications"
            )
        
        # Verify all employees belong to current user
        employee_count = await db.employees.count_documents({
            "id": {"$in": request.employee_ids},
            "user_id": current_user.id
        })
        
        if employee_count != len(request.employee_ids):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Some employees do not belong to your account"
            )
        
        background_tasks.add_task(
            process_batch_verification_authenticated, 
            request.employee_ids, 
            request.verification_types,
            current_user.id
        )
        
        return {
            "message": "Batch verification started",
            "employee_count": len(request.employee_ids),
            "verification_types": request.verification_types,
            "status": "processing"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting batch verification: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_batch_verification_authenticated(
    employee_ids: List[str], 
    verification_types: List[VerificationType],
    user_id: str
):
    """Background task to process batch verification for authenticated user"""
    try:
        for employee_id in employee_ids:
            employee_data = await db.employees.find_one({"id": employee_id, "user_id": user_id})
            if employee_data:
                employee = Employee(**employee_data)
                
                for verification_type in verification_types:
                    if verification_type == VerificationType.OIG:
                        await check_oig_exclusion(employee)
                    elif verification_type == VerificationType.SAM:
                        await check_sam_exclusion(employee)
                    
                    # Add small delay to prevent overwhelming external APIs
                    await asyncio.sleep(0.1)
        
        logger.info(f"Completed batch verification for {len(employee_ids)} employees (user: {user_id})")
    except Exception as e:
        logger.error(f"Error in batch verification: {e}")

@api_router.get("/verification-results")
async def get_all_verification_results(current_user: User = Depends(get_current_user)):
    """Get all verification results for current user's employees"""
    try:
        # Get employee IDs for current user
        employees = await db.employees.find({"user_id": current_user.id}, {"id": 1}).to_list(1000)
        employee_ids = [emp["id"] for emp in employees]
        
        if not employee_ids:
            return []
        
        results = await db.verification_results.find({
            "employee_id": {"$in": employee_ids}
        }).sort("checked_at", -1).to_list(1000)
        
        return [VerificationResult(**result) for result in results]
    except Exception as e:
        logger.error(f"Error fetching verification results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/verification-results/summary")
async def get_verification_summary(current_user: User = Depends(get_current_user)):
    """Get verification results summary/statistics for current user"""
    try:
        # Get employee IDs for current user
        employees = await db.employees.find({"user_id": current_user.id}, {"id": 1}).to_list(1000)
        employee_ids = [emp["id"] for emp in employees]
        
        if not employee_ids:
            return {
                "total_checks": 0,
                "by_status": {},
                "by_type": {}
            }
        
        # Get counts by status
        pipeline = [
            {"$match": {"employee_id": {"$in": employee_ids}}},
            {
                "$group": {
                    "_id": {"status": "$status", "verification_type": "$verification_type"},
                    "count": {"$sum": 1}
                }
            }
        ]
        
        results = await db.verification_results.aggregate(pipeline).to_list(100)
        
        total_results = await db.verification_results.find({
            "employee_id": {"$in": employee_ids}
        }).to_list(10000)
        
        summary = {
            "total_checks": len(total_results),
            "by_status": {},
            "by_type": {}
        }
        
        for result in results:
            status = result["_id"]["status"]
            vtype = result["_id"]["verification_type"]
            count = result["count"]
            
            if status not in summary["by_status"]:
                summary["by_status"][status] = 0
            summary["by_status"][status] += count
            
            if vtype not in summary["by_type"]:
                summary["by_type"][vtype] = 0
            summary["by_type"][vtype] += count
        
        return summary
    except Exception as e:
        logger.error(f"Error getting verification summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize the application"""
    logger.info("Health Verify Now API starting up...")
    
    # Download and load OIG data on startup
    logger.info("Initializing OIG exclusion database...")
    if await load_oig_data_to_memory():
        logger.info("✅ OIG exclusion database loaded successfully")
    else:
        logger.warning("⚠️ Failed to load OIG exclusion database - will attempt download on first check")
    
    # Download and load SAM data on startup
    logger.info("Initializing SAM exclusion database...")
    if await load_sam_data_to_memory():
        logger.info("✅ SAM exclusion database loaded successfully")
    else:
        logger.warning("⚠️ Failed to load SAM exclusion database - will attempt download on first check")
    
    logger.info("🚀 Health Verify Now API ready for commercial use!")
    logger.info("   - OIG verification: Real-time searches against downloaded database")
    logger.info("   - SAM verification: Real-time searches against downloaded database")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
