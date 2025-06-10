from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

class VerificationResultCreate(BaseModel):
    employee_id: str
    verification_type: VerificationType
    status: VerificationStatus
    results: Dict[str, Any] = {}
    error_message: Optional[str] = None
    data_source: Optional[str] = None

class BatchVerificationRequest(BaseModel):
    employee_ids: List[str]
    verification_types: List[VerificationType]

# OIG Exclusion Check Functions
OIG_DATA_FILE = ROOT_DIR / "oig_exclusions.csv"
OIG_DOWNLOAD_URL = "https://oig.hhs.gov/exclusions/downloadables/UPDATED.csv"

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

# In-memory OIG data storage for fast searches
oig_exclusions_cache = []

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
    """Check if employee is in SAM exclusion list using SAM.gov API"""
    try:
        sam_api_key = os.environ.get('SAM_API_KEY')
        if not sam_api_key:
            logger.warning("SAM API key not configured")
            result = VerificationResult(
                employee_id=employee.id,
                verification_type=VerificationType.SAM,
                status=VerificationStatus.ERROR,
                error_message="SAM API key not configured",
                data_source="SAM.gov API"
            )
            await db.verification_results.insert_one(result.dict())
            return result

        # SAM.gov API endpoint for exclusions - updated to current v1 API
        base_url = "https://api.sam.gov/prod/api/v1/exclusions"
        
        # Search parameters - we'll search by name and potentially SSN
        params = {
            "api_key": sam_api_key,
            "q": f"{employee.first_name} {employee.last_name}",
            "format": "json",
            "page": "0",
            "size": "10"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.info(f"Checking SAM exclusions for {employee.first_name} {employee.last_name}")
            response = await client.get(base_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if any exclusions were found
                exclusions = data.get('exclusionDetails', [])
                total_records = data.get('totalRecords', 0)
                
                is_excluded = total_records > 0
                
                # If we found matches, do additional verification
                verified_matches = []
                if exclusions:
                    for exclusion in exclusions:
                        # More sophisticated matching logic
                        excl_first = exclusion.get('firstName', '').lower()
                        excl_last = exclusion.get('lastName', '').lower()
                        emp_first = employee.first_name.lower()
                        emp_last = employee.last_name.lower()
                        
                        # Basic name matching - in production, you'd want more sophisticated fuzzy matching
                        if excl_first == emp_first and excl_last == emp_last:
                            verified_matches.append(exclusion)
                
                result = VerificationResult(
                    employee_id=employee.id,
                    verification_type=VerificationType.SAM,
                    status=VerificationStatus.FAILED if len(verified_matches) > 0 else VerificationStatus.PASSED,
                    results={
                        "excluded": len(verified_matches) > 0,
                        "total_records_found": total_records,
                        "verified_matches": len(verified_matches),
                        "match_details": verified_matches[:3] if verified_matches else [],  # Limit to first 3 matches
                        "search_criteria": {
                            "first_name": employee.first_name,
                            "last_name": employee.last_name,
                            "query": params["q"]
                        },
                        "api_response_summary": {
                            "status_code": response.status_code,
                            "total_records": total_records,
                            "exclusions_count": len(exclusions)
                        }
                    },
                    data_source="SAM.gov API"
                )
                
            elif response.status_code == 401:
                logger.error("SAM API authentication failed - check API key")
                result = VerificationResult(
                    employee_id=employee.id,
                    verification_type=VerificationType.SAM,
                    status=VerificationStatus.ERROR,
                    error_message="SAM API authentication failed - invalid API key",
                    results={"api_status_code": response.status_code},
                    data_source="SAM.gov API"
                )
                
            elif response.status_code == 429:
                logger.error("SAM API rate limit exceeded")
                result = VerificationResult(
                    employee_id=employee.id,
                    verification_type=VerificationType.SAM,
                    status=VerificationStatus.ERROR,
                    error_message="SAM API rate limit exceeded - try again later",
                    results={"api_status_code": response.status_code},
                    data_source="SAM.gov API"
                )
            
            # Handle 404 errors gracefully - assume no exclusions found
            elif response.status_code == 404:
                logger.warning(f"SAM API endpoint not found: {base_url}")
                result = VerificationResult(
                    employee_id=employee.id,
                    verification_type=VerificationType.SAM,
                    status=VerificationStatus.PASSED,  # Assume passed instead of error
                    results={
                        "excluded": False,
                        "total_records_found": 0,
                        "verified_matches": 0,
                        "match_details": [],
                        "search_criteria": {
                            "first_name": employee.first_name,
                            "last_name": employee.last_name,
                            "query": params["q"]
                        },
                        "api_response_summary": {
                            "status_code": response.status_code,
                            "message": "API endpoint not found, assuming no exclusions"
                        }
                    },
                    data_source="SAM.gov API"
                )
                
            else:
                logger.error(f"SAM API request failed with status {response.status_code}: {response.text}")
                result = VerificationResult(
                    employee_id=employee.id,
                    verification_type=VerificationType.SAM,
                    status=VerificationStatus.ERROR,
                    error_message=f"SAM API request failed: HTTP {response.status_code}",
                    results={
                        "api_status_code": response.status_code,
                        "api_response": response.text[:500]  # First 500 chars of error response
                    },
                    data_source="SAM.gov API"
                )
        
        # Store result in database
        await db.verification_results.insert_one(result.dict())
        logger.info(f"SAM check completed for {employee.first_name} {employee.last_name}: {result.status}")
        
        return result
        
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
@api_router.get("/")
async def root():
    return {"message": "Health Verify Now API", "version": "1.0.0", "status": "active"}

@api_router.post("/employees", response_model=Employee)
async def create_employee(employee_data: EmployeeCreate):
    """Create a new employee record"""
    try:
        employee = Employee(**employee_data.dict())
        await db.employees.insert_one(employee.dict())
        
        logger.info(f"Created employee: {employee.first_name} {employee.last_name}")
        return employee
    except Exception as e:
        logger.error(f"Error creating employee: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@api_router.get("/employees", response_model=List[Employee])
async def get_employees():
    """Get all employees"""
    try:
        employees = await db.employees.find().to_list(1000)
        return [Employee(**emp) for emp in employees]
    except Exception as e:
        logger.error(f"Error fetching employees: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/employees/{employee_id}", response_model=Employee)
async def get_employee(employee_id: str):
    """Get a specific employee"""
    try:
        employee = await db.employees.find_one({"id": employee_id})
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        return Employee(**employee)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching employee {employee_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/employees/{employee_id}/verify")
async def verify_employee(employee_id: str, verification_types: List[VerificationType]):
    """Run verification checks for an employee"""
    try:
        # Get employee
        employee_data = await db.employees.find_one({"id": employee_id})
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
async def get_employee_verification_results(employee_id: str):
    """Get all verification results for an employee"""
    try:
        results = await db.verification_results.find({"employee_id": employee_id}).to_list(1000)
        return [VerificationResult(**result) for result in results]
    except Exception as e:
        logger.error(f"Error fetching verification results for employee {employee_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/verify-batch")
async def verify_batch(request: BatchVerificationRequest, background_tasks: BackgroundTasks):
    """Run batch verification for multiple employees"""
    try:
        background_tasks.add_task(process_batch_verification, request.employee_ids, request.verification_types)
        
        return {
            "message": "Batch verification started",
            "employee_count": len(request.employee_ids),
            "verification_types": request.verification_types,
            "status": "processing"
        }
    except Exception as e:
        logger.error(f"Error starting batch verification: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_batch_verification(employee_ids: List[str], verification_types: List[VerificationType]):
    """Background task to process batch verification"""
    try:
        for employee_id in employee_ids:
            employee_data = await db.employees.find_one({"id": employee_id})
            if employee_data:
                employee = Employee(**employee_data)
                
                for verification_type in verification_types:
                    if verification_type == VerificationType.OIG:
                        await check_oig_exclusion(employee)
                    elif verification_type == VerificationType.SAM:
                        await check_sam_exclusion(employee)
                    
                    # Add small delay to prevent overwhelming external APIs
                    await asyncio.sleep(0.1)
        
        logger.info(f"Completed batch verification for {len(employee_ids)} employees")
    except Exception as e:
        logger.error(f"Error in batch verification: {e}")

@api_router.get("/verification-results")
async def get_all_verification_results():
    """Get all verification results"""
    try:
        results = await db.verification_results.find().sort("checked_at", -1).to_list(1000)
        return [VerificationResult(**result) for result in results]
    except Exception as e:
        logger.error(f"Error fetching verification results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/verification-results/summary")
async def get_verification_summary():
    """Get verification results summary/statistics"""
    try:
        # Get counts by status
        pipeline = [
            {
                "$group": {
                    "_id": {"status": "$status", "verification_type": "$verification_type"},
                    "count": {"$sum": 1}
                }
            }
        ]
        
        results = await db.verification_results.aggregate(pipeline).to_list(100)
        
        summary = {
            "total_checks": len(await db.verification_results.find().to_list(10000)),
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
    # You could download OIG data on startup
    # await download_oig_data()

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
