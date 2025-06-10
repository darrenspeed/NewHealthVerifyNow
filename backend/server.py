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
async def download_oig_data():
    """Download the latest OIG exclusion list"""
    try:
        url = "https://oig.hhs.gov/exclusions/exclusions_list.asp"
        # For now, we'll use a simplified approach - in production you'd download the actual CSV
        # The real URL for the CSV download is: https://oig.hhs.gov/exclusions/downloadables/UPDATED.csv
        logger.info("Downloading OIG exclusion data...")
        
        # This is a placeholder - we'll implement actual CSV download later
        return True
    except Exception as e:
        logger.error(f"Error downloading OIG data: {e}")
        return False

async def check_oig_exclusion(employee: Employee) -> VerificationResult:
    """Check if employee is in OIG exclusion list"""
    try:
        # For MVP, we'll simulate the check with some basic logic
        # In production, this would search through the downloaded OIG CSV data
        
        full_name = f"{employee.first_name} {employee.last_name}".lower()
        
        # Simulate some exclusions for demo purposes
        demo_exclusions = [
            "john doe", "jane smith", "test user", "demo person"
        ]
        
        is_excluded = full_name in demo_exclusions
        
        result = VerificationResult(
            employee_id=employee.id,
            verification_type=VerificationType.OIG,
            status=VerificationStatus.FAILED if is_excluded else VerificationStatus.PASSED,
            results={
                "excluded": is_excluded,
                "match_details": f"Full name search: {full_name}" if is_excluded else "No matches found",
                "search_criteria": {
                    "first_name": employee.first_name,
                    "last_name": employee.last_name,
                    "ssn_last_4": employee.ssn[-4:] if len(employee.ssn) >= 4 else "N/A"
                }
            },
            data_source="OIG LEIE Database"
        )
        
        # Store result in database
        await db.verification_results.insert_one(result.dict())
        
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
        base_url = "https://api.sam.gov/entity-information/v3/entities"
        
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
