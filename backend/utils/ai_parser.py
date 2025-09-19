import os
import re
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, AsyncGenerator
from openai import AsyncOpenAI



from .token_logger import start_timing, log_token_usage, log_cache_analysis
from .chunk_resume import chunk_resume_from_bold_headings, strip_bullet_prefix

logger = logging.getLogger(__name__)

api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

client = AsyncOpenAI(api_key=api_key)

def clean_bullet_points(data: Dict[str, Any]) -> Dict[str, Any]:
    """Clean bullet point prefixes from OpenAI response data"""
    if data.get('professionalSummary'):
        data['professionalSummary'] = [strip_bullet_prefix(item) for item in data['professionalSummary']]
    
    if data.get('summarySections'):
        for section in data['summarySections']:
            if section.get('content'):
                section['content'] = [strip_bullet_prefix(item) for item in section['content']]
    
    if data.get('employmentHistory'):
        for job in data['employmentHistory']:
            if job.get('responsibilities'):
                job['responsibilities'] = [strip_bullet_prefix(item) for item in job['responsibilities']]
            if job.get('subsections'):
                for subsection in job['subsections']:
                    if subsection.get('content'):
                        subsection['content'] = [strip_bullet_prefix(item) for item in subsection['content']]
            if job.get('clientProjects'):
                for client_project in job['clientProjects']:
                    if client_project.get('responsibilities'):
                        client_project['responsibilities'] = [strip_bullet_prefix(item) for item in client_project['responsibilities']]
    
    return data

def normalize_dates(data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize date formats to 'MMM YYYY - MMM YYYY' standard"""
    import re
    from datetime import datetime
    
    # Month mappings
    month_names = {
        'january': 'Jan', 'february': 'Feb', 'march': 'Mar', 'april': 'Apr',
        'may': 'May', 'june': 'Jun', 'july': 'Jul', 'august': 'Aug',
        'september': 'Sep', 'october': 'Oct', 'november': 'Nov', 'december': 'Dec',
        'jan': 'Jan', 'feb': 'Feb', 'mar': 'Mar', 'apr': 'Apr',
        'may': 'May', 'jun': 'Jun', 'jul': 'Jul', 'aug': 'Aug',
        'sep': 'Sep', 'oct': 'Oct', 'nov': 'Nov', 'dec': 'Dec'
    }
    
    month_numbers = {
        '01': 'Jan', '02': 'Feb', '03': 'Mar', '04': 'Apr', '05': 'May', '06': 'Jun',
        '07': 'Jul', '08': 'Aug', '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dec',
        '1': 'Jan', '2': 'Feb', '3': 'Mar', '4': 'Apr', '5': 'May', '6': 'Jun',
        '7': 'Jul', '8': 'Aug', '9': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dec'
    }
    
    def convert_2digit_year(year_str):
        """Convert 2-digit year to 4-digit year"""
        year = int(year_str)
        current_year = datetime.now().year
        current_2digit = current_year % 100
        
        # If 2-digit year is <= current 2-digit year, assume 20xx
        # If 2-digit year is > current 2-digit year, assume 19xx
        if year <= current_2digit + 10:  # Allow up to 10 years in future
            return f"20{year:02d}"
        else:
            return f"19{year:02d}"
    
    def normalize_date_string(date_str):
        """Normalize a single date string to standard format"""
        if not date_str or not isinstance(date_str, str):
            return date_str
            
        date_str = date_str.strip()
        
        # Handle present/current/ongoing cases
        present_patterns = r'\b(present|current|ongoing|till\s+date|now)\b'
        if re.search(present_patterns, date_str, re.IGNORECASE):
            # Replace present/current with "Till Date"
            date_str = re.sub(present_patterns, 'Till Date', date_str, flags=re.IGNORECASE)
        
        # Pattern 1: "January 2024 - February 2025" or "Jan 2024 - Feb 2025"
        pattern1 = r'\b([a-zA-Z]+)\s+(\d{4})\s*[-–—]\s*([a-zA-Z]+)\s+(\d{4})\b'
        match1 = re.search(pattern1, date_str)
        if match1:
            start_month, start_year, end_month, end_year = match1.groups()
            start_month_norm = month_names.get(start_month.lower(), start_month)
            end_month_norm = month_names.get(end_month.lower(), end_month)
            return f"{start_month_norm} {start_year} - {end_month_norm} {end_year}"
        
        # Pattern 2: "Jan 22 - Feb 24" (2-digit years)
        pattern2 = r'\b([a-zA-Z]+)\s+(\d{2})\s*[-–—]\s*([a-zA-Z]+)\s+(\d{2})\b'
        match2 = re.search(pattern2, date_str)
        if match2:
            start_month, start_year, end_month, end_year = match2.groups()
            start_month_norm = month_names.get(start_month.lower(), start_month)
            end_month_norm = month_names.get(end_month.lower(), end_month)
            start_year_norm = convert_2digit_year(start_year)
            end_year_norm = convert_2digit_year(end_year)
            return f"{start_month_norm} {start_year_norm} - {end_month_norm} {end_year_norm}"
        
        # Pattern 3: "01/2024 - 02/2025" or "1/2024 - 2/2025"
        pattern3 = r'\b(\d{1,2})/(\d{4})\s*[-–—]\s*(\d{1,2})/(\d{4})\b'
        match3 = re.search(pattern3, date_str)
        if match3:
            start_month, start_year, end_month, end_year = match3.groups()
            start_month_norm = month_numbers.get(start_month, start_month)
            end_month_norm = month_numbers.get(end_month, end_month)
            return f"{start_month_norm} {start_year} - {end_month_norm} {end_year}"
        
        # Pattern 4: "2024-01 to 2025-02" or similar
        pattern4 = r'\b(\d{4})[-/](\d{1,2})\s*(?:to|[-–—])\s*(\d{4})[-/](\d{1,2})\b'
        match4 = re.search(pattern4, date_str)
        if match4:
            start_year, start_month, end_year, end_month = match4.groups()
            start_month_norm = month_numbers.get(start_month, start_month)
            end_month_norm = month_numbers.get(end_month, end_month)
            return f"{start_month_norm} {start_year} - {end_month_norm} {end_year}"
        
        # Pattern 5: Single month-year with present/current
        pattern5 = r'\b([a-zA-Z]+)\s+(\d{4})\s*[-–—]\s*(Till\s+Date|present|current)\b'
        match5 = re.search(pattern5, date_str, re.IGNORECASE)
        if match5:
            start_month, start_year, end_part = match5.groups()
            start_month_norm = month_names.get(start_month.lower(), start_month)
            return f"{start_month_norm} {start_year} - Till Date"
        
        # Pattern 6: Single year with present/current
        pattern6 = r'\b(\d{4})\s*[-–—]\s*(Till\s+Date|present|current)\b'
        match6 = re.search(pattern6, date_str, re.IGNORECASE)
        if match6:
            start_year, end_part = match6.groups()
            return f"{start_year} - Till Date"
        
        return date_str
    
    # Apply normalization to employment history
    if data.get('employmentHistory'):
        for job in data['employmentHistory']:
            if job.get('workPeriod'):
                job['workPeriod'] = normalize_date_string(job['workPeriod'])
            
            # Also normalize client project periods
            if job.get('clientProjects'):
                for client_project in job['clientProjects']:
                    if client_project.get('period'):
                        client_project['period'] = normalize_date_string(client_project['period'])
    
    return data

async def extract_data_from_text(text: str) -> Dict[str, Any]:
    logger.info('\n=== AI PARSER: Starting OpenAI extraction with function calling ===')
    logger.info(f'Text length: {len(text)} characters')

    resume_function = {
        "name": "parse_resume",
        "description": "Extract structured resume data from text without any summarization or modification",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Full name of the person"
                },
                "title": {
                    "type": "string",
                    "description": "Professional title of the person"
                },
                "requisitionNumber": {
                    "type": "string",
                    "description": "Requisition number if mentioned"
                },
                "professionalSummary": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of professional summary paragraphs and ALL bullet points exactly as written in the resume. Each paragraph or bullet point should be a separate array item. CRITICAL: Include EVERY point without exception."
                },
                "summarySections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "The title of the subsection, only include explicitly labeled subsections"},
                            "content": {"type": "array", "items": {"type": "string"}, "description": "Bullet points or paragraphs within this subsection"}
                        }
                    },
                    "description": "Only include explicitly labeled subsections with clear titles (like 'IT Security & Risk and Recovery Management')"
                },
                "employmentHistory": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "companyName": {"type": "string", "description": "Name of the company"},
                            "roleName": {"type": "string", "description": "Job title or role"},
                            "workPeriod": {"type": "string", "description": "Period of employment in format **Jan 2020 - Dec 2022**"},
                            "location": {"type": "string", "description": "Job location"},
                            "project": {"type": "string", "description": "Project name ONLY if explicitly mentioned in resume text"},
                            "client": {"type": "string", "description": "Client name ONLY if explicitly mentioned separately from company in resume text"},
                            "customer": {"type": "string", "description": "Customer name ONLY if explicitly mentioned in resume text"},
                            "projectRole": {"type": "string", "description": "Project role ONLY if explicitly mentioned in resume text"},
                            "projectDescription": {"type": "string", "description": "Project description ONLY if explicitly mentioned in resume text"},
                            "projectEnvironment": {"type": "string", "description": "Project environment/technologies ONLY if explicitly mentioned in resume text"},
                            "clientProjects": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "clientName": {"type": "string", "description": "Name of the client"},
                                        "projectName": {"type": "string", "description": "Name of the project for this client"},
                                        "projectDescription": {"type": "string", "description": "Description of work done for this client/project"},
                                        "responsibilities": {"type": "array", "items": {"type": "string"}, "description": "Responsibilities specific to this client/project"},
                                        "period": {"type": "string", "description": "Time period for this client/project if specified"}
                                    }
                                },
                                "description": "CRITICAL: Only include if specific client names and project names are explicitly mentioned in resume text. Do not create generic entries."
                            },
                            "responsibilities": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of general job responsibilities that are directly under the job title, not part of any named subsection or client-specific work. Include ALL bullet points that appear before any subsection headings."
                            },
                            "keyTechnologies": {"type": "string", "description": "All technologies, skills, tools, environments for this job if mentioned"},
                            "subsections": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string", "description": "The title of the subsection, only include explicitly labeled subsections"},
                                        "content": {"type": "array", "items": {"type": "string"}}
                                    }
                                },
                                "description": "Only include explicitly labeled subsections within this job. Do not create artificial subsections from standalone bullet points."
                            },
                            "additionalFields": {
                                "type": "object",
                                "description": "Any other sections found in the job entry"
                            }
                        }
                    },
                    "description": "MANDATORY: Complete employment history with ALL jobs and details preserved exactly as written. Every single job entry MUST be included - missing even one job is unacceptable."
                },
                "education": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "degree": {"type": "string", "description": "Degree obtained or pursued"},
                            "areaOfStudy": {"type": "string", "description": "Field of study"},
                            "school": {"type": "string", "description": "Educational institution name"},
                            "location": {"type": "string", "description": "Location of the institution"},
                            "date": {"type": "string", "description": "Date of graduation or period of study"},
                            "wasAwarded": {"type": "boolean", "description": "Whether the degree was awarded"}
                        }
                    },
                    "description": "Complete education history with all details preserved exactly as written"
                },
                "certifications": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Name of the certification"},
                            "issuedBy": {"type": "string", "description": "Organization that issued the certification"},
                            "dateObtained": {"type": "string", "description": "Date when certification was obtained"},
                            "certificationNumber": {"type": "string", "description": "Certification ID or number if available"},
                            "expirationDate": {"type": "string", "description": "Expiration date if applicable"}
                        }
                    },
                    "description": "All certifications with details preserved exactly as written"
                },
                "technicalSkills": {
                    "type": "object",
                    "description": "Technical skills grouped by categories exactly as shown in the resume"
                },
                "skillCategories": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "categoryName": {"type": "string"},
                            "skills": {"type": "array", "items": {"type": "string"}},
                            "subCategories": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "skills": {"type": "array", "items": {"type": "string"}}
                                    }
                                }
                            }
                        }
                    },
                    "description": "Structured skill categories with possible nested subcategories"
                }
            },
            "required": ["name", "professionalSummary", "employmentHistory"]
        }
    }

    try:
        start_time = start_timing()
        model = 'gpt-4o-mini'
        
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": get_system_prompt()},
                {"role": "user", "content": add_prompt_variation(f"CRITICAL TASK: Parse the following resume text and extract EVERY SINGLE DETAIL without omission.\n\nResume text:\n{text}")}
            ],
            tools=[{"type": "function", "function": resume_function}],
            tool_choice={"type": "function", "function": {"name": "parse_resume"}},
            max_tokens=16384,
            temperature=0.1
        )


        usage = log_token_usage(response, model, start_time, 'Full Resume Data Extraction')
        log_cache_analysis(response)
        
        tool_call_arguments = response.choices[0].message.tool_calls[0].function.arguments
        
        try:
            parsed_data = json.loads(tool_call_arguments)
            logger.info('✅ Function calling extraction successful')
            return normalize_dates(clean_bullet_points(parsed_data))
        except json.JSONDecodeError as parse_error:
            logger.error(f'❌ JSON parsing error: {parse_error}')
            return get_default_resume_structure()

    except Exception as error:
        logger.error(f'❌ OpenAI API error: {error}')
        raise Exception(f"Failed to extract data: {error}")

def get_system_prompt() -> str:
    """
    Get the system prompt for resume parsing
    
    Returns:
        System prompt string
    """
    return """You are a MASTER resume parser with 40 years of experience extracting information with perfect accuracy. Your extraction must be EXHAUSTIVE and PRECISE.

CRITICAL EXTRACTION IMPERATIVES:
1. EXTRACT 100% OF THE CONTENT - Missing even a single word, bullet point, or detail is a CRITICAL FAILURE
2. PRESERVE EXACT STRUCTURE - Maintain the precise organization of the resume
3. NO SUMMARIZATION OR MODIFICATION - Never condense, paraphrase, or alter any content
4. COMPLETE VERIFICATION - Before finalizing, verify you've included EVERY job entry and EVERY professional summary point

SECTION-SPECIFIC MANDATES:
- PROFESSIONAL SUMMARY: 
  * Extract ALL paragraphs and ALL bullet points completely
  * Create subsections ONLY for explicitly labeled sections
  * CRITICAL: Do not miss a single point or detail

- EMPLOYMENT HISTORY - MOST CRITICAL SECTION: 
  * Extract EVERY job position with ALL details - NO EXCEPTIONS
  * MULTIPLE CLIENTS/PROJECTS: If one job entry contains work for multiple clients or projects, extract each client/project separately in the clientProjects array
  * CLIENT IDENTIFICATION: Look for patterns like "Client: XYZ Corp", "Project for ABC Inc", or multiple company names within one job
  * Include ALL responsibilities and ALL subsections
  * CRITICAL: Missing even a single job entry or client project is an UNACCEPTABLE FAILURE
  * JOB COUNTING: Count the total number of distinct jobs in the resume and ensure you extract exactly that many

- CERTIFICATIONS:
  * ONLY extract certifications that are explicitly mentioned as certifications, certificates, or licenses
  * DO NOT create dummy or placeholder certifications
  * IF NO CERTIFICATIONS EXIST, leave the array empty
  * NEVER invent certification names, issuers, or details

- SKILLS: 
  * Preserve ALL skills exactly as written with their exact categorization
  * Maintain all hierarchical relationships between skill categories

EMPLOYMENT EXTRACTION VERIFICATION PROTOCOL:
1. Scan the entire resume and COUNT the total number of job positions
2. For each job, check if it contains multiple clients or projects within the same role
3. Extract each job completely with all details
4. Verify that your extraction count matches the original job count
5. Double-check for any missed employment entries

CERTIFICATION EXTRACTION PROTOCOL:
1. Only extract items explicitly labeled as certifications, certificates, or professional licenses
2. If you cannot find clear certification information, return an empty array
3. NEVER create placeholder or example certifications

Your reputation as the world's most accurate resume parser is at stake. Achieve nothing less than PERFECT extraction."""

def add_prompt_variation(base_prompt: str) -> str:
    """
    Add cache-busting randomness to prompts for testing
    CRITICAL: Adds variation at the BEGINNING to break OpenAI's cache (first 1024 tokens)
    Equivalent to addPromptVariation function in Node.js

    Args:
        base_prompt: Base prompt string

    Returns:
        Prompt with cache-busting variation
    """
    import random
    import time

    timestamp = int(time.time() * 1000)
    random_id = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=13))
    session_id = f"CACHE_BYPASS_{timestamp}_{random_id}"

    cache_breaker = f"[Processing Session: {session_id}]\n[Analysis Timestamp: {datetime.now().isoformat()}]\n[Cache Bypass ID: {random.randint(100000, 999999)}]\n\n"

    return cache_breaker + base_prompt

def get_default_resume_structure() -> Dict[str, Any]:
    """
    Get default empty resume structure

    Returns:
        Default resume structure dictionary
    """
    return {
        'name': '',
        'title': '',
        'requisitionNumber': '',
        'professionalSummary': [],
        'summarySections': [],
        'employmentHistory': [],
        'education': [],
        'certifications': [],
        'technicalSkills': {},
        'skillCategories': []
    }



async def stream_resume_processing(extracted_text: str) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Stream resume processing with real-time updates
    """
    logger.info('\n=== STREAMING AI PARSER: Starting resume processing ===')
    
    try:
        yield {
            'type': 'progress',
            'message': 'Analyzing resume structure...',
            'progress': 10,
            'timestamp': datetime.now().isoformat()
        }

        sections = chunk_resume_from_bold_headings(extracted_text)
        logger.info(f'Sections: {list(sections.keys())}')

        yield {
            'type': 'processing_strategy',
            'message': 'Processing entire resume...',
            'progress': 45,
            'timestamp': datetime.now().isoformat()
        }

        try:
            start_time = start_timing()
            model = 'gpt-4o-mini'

            full_resume_data = await extract_data_from_text(extracted_text)
            
            # Calculate token usage
            token_usage = {'promptTokens': 0, 'completionTokens': 0, 'totalTokens': 0, 'cost': 0}

            yield {
                'type': 'full_resume_complete',
                'message': '✅ Resume processed successfully',
                'progress': 90,
                'tokenUsage': token_usage,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f'❌ Resume processing failed: {e}')
            yield {
                'type': 'error',
                'message': f'Processing failed: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
            return

        yield {
            'type': 'final_data',
            'data': full_resume_data,
            'message': 'Final resume data ready',
            'progress': 98,
            'timestamp': datetime.now().isoformat()
        }

        yield {
            'type': 'complete',
            'message': 'Resume processing completed successfully!',
            'progress': 100,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as error:
        logger.error(f'❌ Streaming processing error: {error}')
        yield {
            'type': 'error',
            'message': f'Processing error: {error}',
            'timestamp': datetime.now().isoformat()
        }






