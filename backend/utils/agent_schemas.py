"""
Agent Schema Definitions for Resume Processing
Modular, maintainable function schemas for specialized AI agents
"""

from typing import Dict, Any

class ResumeAgentSchemas:
    """
    Centralized schema definitions for resume processing agents.
    Each schema is focused on a specific resume section for optimal extraction.
    """
    
    @staticmethod
    def get_header_agent_schema() -> Dict[str, Any]:
        """Schema for extracting personal information and header details"""
        return {
            "name": "extract_header_info",
            "description": "Extract personal information and header details from resume",
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
                        "description": "Requisition number if mentioned in the resume"
                    }
                },
                "required": ["name"]
            }
        }
    
    @staticmethod
    def get_summary_agent_schema() -> Dict[str, Any]:
        """Schema for extracting professional summary and overview sections"""
        return {
            "name": "extract_professional_summary",
            "description": "Extract professional summary, career overview, and profile sections",
            "parameters": {
                "type": "object",
                "properties": {
                    "professionalSummary": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of professional summary paragraphs and bullet points exactly as written. Each paragraph or bullet point should be a separate array item. Include EVERY point without exception."
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
                        "description": "Only include explicitly labeled subsections with clear titles"
                    }
                },
                "required": ["professionalSummary"]
            }
        }
    
    @staticmethod
    def get_experience_agent_schema() -> Dict[str, Any]:
        """Schema for extracting employment history and work experience"""
        return {
            "name": "extract_employment_history",
            "description": "Extract complete employment history with all job details",
            "parameters": {
                "type": "object",
                "properties": {
                    "employmentHistory": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "companyName": {"type": "string", "description": "Name of the company. If clients are mentioned, format as 'CompanyName (Client1, Client2, Client3)' with all client names separated by commas"},
                                "roleName": {"type": "string", "description": "Job title or role"},
                                "workPeriod": {
                                    "type": "string",
                                    "pattern": "^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \\d{4} - (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \\d{4}$|^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \\d{4} - Till Date$",
                                    "description": "MUST be exact format: MMM YYYY - MMM YYYY (e.g., Jun 2024 - Sep 2025) or MMM YYYY - Till Date for current positions. Use 'Till Date' (not 'current' or 'present') for ongoing employment."
                                },
                                "location": {
                                    "type": "string",
                                    "pattern": "^[A-Za-z\\s]+, [A-Za-z\\s]+$",
                                    "description": "MUST be exact format: City, State/Country (e.g., Hyderabad, India or Dallas, TX). For US locations, use state abbreviations (TX, CA, NY, etc.)"
                                },

                                "projects": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "projectName": {"type": "string", "description": "Format as 'Project N: ProjectTitle/ Role' where N is descending number (Project 5, Project 4, etc.) with most recent project having highest number. Example: 'Project 4: RWE Datacenter-Transition/ Senior Database Administrator'"},
                                            "projectResponsibilities": {"type": "array", "items": {"type": "string"}, "description": "List of responsibilities and achievements specific to this project"},
                                            "keyTechnologies": {"type": "string", "description": "Technologies, tools, and skills used in this specific project"},
                                            "period": {"type": "string", "description": "Time period for this project, should match or be within the overall workPeriod of the job"}
                                        }
                                    },
                                    "description": "CRITICAL: ONLY include this field if the resume explicitly mentions specific named projects for this job. If no projects are mentioned, return an empty array []. DO NOT create or invent projects. Look for clear project names, project titles, or project-specific sections in that specific job entry."
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
                                            "title": {"type": "string"},
                                            "content": {"type": "array", "items": {"type": "string"}}
                                        }
                                    },
                                    "description": "Only include explicitly labeled subsections within this job. Do not create artificial subsections from standalone bullet points."
                                }
                            }
                        },
                        "description": "MANDATORY: Complete employment history with ALL jobs and details preserved exactly as written. Every single job entry MUST be included - missing even one job is unacceptable."
                    }
                },
                "required": ["employmentHistory"]
            }
        }
    
    @staticmethod
    def get_education_agent_schema() -> Dict[str, Any]:
        """Schema for extracting education and academic background"""
        return {
            "name": "extract_education_history",
            "description": "Extract complete education history and academic qualifications",
            "parameters": {
                "type": "object",
                "properties": {
                    "education": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "degree": {"type": "string", "description": "Degree obtained or pursued"},
                                "areaOfStudy": {"type": "string", "description": "Field of study or major"},
                                "school": {"type": "string", "description": "Educational institution name ONLY - exclude location information"},
                                "location": {
                                    "type": "string",
                                    "pattern": "^[A-Za-z\\s]+, [A-Za-z\\s]+$",
                                    "description": "MUST be exact format: City, State/Country (e.g., Hyderabad, India or Austin, TX). For US locations, use state abbreviations (TX, CA, NY, etc.). Extract separately even if combined with school name."
                                },
                                "date": {"type": "string", "description": "Date of graduation or study period"},
                                "wasAwarded": {"type": "boolean", "description": "Whether the degree was awarded it must be always 'yes', unless it is mentioned as 'no'"}
                            }
                        },
                        "description": "Complete education history with all details preserved exactly as written"
                    }
                },
                "required": ["education"]
            }
        }
    
    @staticmethod
    def get_skills_agent_schema() -> Dict[str, Any]:
        """Schema for extracting technical skills and competencies"""
        return {
            "name": "extract_technical_skills",
            "description": "Extract technical skills, competencies, and skill categories",
            "parameters": {
                "type": "object",
                "properties": {
                    "technicalSkills": {
                        "type": "object",
                        "description": "Technical skills grouped by categories exactly as shown in resume"
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
                "required": []
            }
        }
    
    @staticmethod
    def get_certifications_agent_schema() -> Dict[str, Any]:
        """Schema for extracting certifications and professional licenses"""
        return {
            "name": "extract_certifications",
            "description": "Extract certifications, licenses, and professional credentials",
            "parameters": {
                "type": "object",
                "properties": {
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
                        "description": "All certifications with details preserved exactly as written. Only extract explicitly mentioned certifications."
                    }
                },
                "required": ["certifications"]
            }
        }