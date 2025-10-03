"""
Multi-Agent Resume Processing System
Simplified version with 6 specialized agents for parallel processing
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass
from enum import Enum

from openai import AsyncOpenAI
from .agent_schemas import ResumeAgentSchemas
from .token_logger import start_timing, log_cache_analysis
from .chunk_resume import strip_bullet_prefix

logger = logging.getLogger(__name__)

class AgentType(Enum):
    """Enumeration of available resume processing agents"""
    HEADER = "header"
    SUMMARY = "summary"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    SKILLS = "skills"
    CERTIFICATIONS = "certifications"

@dataclass
class AgentResult:
    """Structured result from an individual agent"""
    agent_type: AgentType
    data: Dict[str, Any]
    processing_time: float
    success: bool
    error_message: Optional[str] = None

class ResumeAgent:
    """
    Individual resume processing agent with specialized extraction capabilities
    """
    
    def __init__(self, client: AsyncOpenAI, agent_type: AgentType):
        self.client = client
        self.agent_type = agent_type
        self.schema = self._get_agent_schema()
        
    def _get_agent_schema(self) -> Dict[str, Any]:
        """Get the appropriate schema for this agent type"""
        schema_map = {
            AgentType.HEADER: ResumeAgentSchemas.get_header_agent_schema,
            AgentType.SUMMARY: ResumeAgentSchemas.get_summary_agent_schema,
            AgentType.EXPERIENCE: ResumeAgentSchemas.get_experience_agent_schema,
            AgentType.EDUCATION: ResumeAgentSchemas.get_education_agent_schema,
            AgentType.SKILLS: ResumeAgentSchemas.get_skills_agent_schema,
            AgentType.CERTIFICATIONS: ResumeAgentSchemas.get_certifications_agent_schema
        }
        return schema_map[self.agent_type]()
    
    def _get_system_prompt(self) -> str:
        """Get specialized system prompt for this agent"""
        base_prompt = """You are a specialized resume extraction agent with 40 years of experience. 
Your task is to extract ONLY the specific section you're responsible for with perfect accuracy.

CRITICAL INSTRUCTIONS:
1. Extract ONLY the section type you're assigned to
2. Preserve ALL content exactly as written - no summarization
3. Maintain original structure and formatting
4. If the section doesn't exist, return empty arrays/objects
5. Never invent or hallucinate information
6. PROJECTS RULE: Only include projects if they are explicitly mentioned in the resume text. If no projects are mentioned for a job, return empty projects array."""

        section_specific = {
            AgentType.HEADER: "Focus ONLY on personal information: name, title, contact details, requisition numbers.",
            AgentType.SUMMARY: "Extract ONLY professional summary, career overview, and profile sections. Include ALL bullet points and paragraphs.",
            AgentType.EXPERIENCE: """Extract ONLY employment history and work experience. Include ALL jobs with complete details. Missing any job is unacceptable. 

CRITICAL PROJECT EXTRACTION RULES:
- ONLY include 'projects' if explicitly mentioned specific named projects, project titles, or project-specific work for that job, if it is outside that particular job entry dont add.
- If a job only lists general responsibilities without mentioning specific projects, return projects as empty array []
""",
            AgentType.EDUCATION: "Extract ONLY education, academic background, and degrees. Include ALL educational entries.",
            AgentType.SKILLS: "Extract ONLY technical skills, competencies, and skill categories. Preserve exact categorization.",
            AgentType.CERTIFICATIONS: "Extract ONLY certifications, licenses, and professional credentials. Only include explicitly mentioned certifications."
        }
        
        return f"{base_prompt}\n\nSPECIFIC FOCUS: {section_specific[self.agent_type]}"
    
    def _add_cache_variation(self, text: str) -> str:
        """Add cache-busting variation to prevent OpenAI caching"""
        import random
        import time
        
        timestamp = int(time.time() * 1000)
        random_id = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
        agent_session = f"AGENT_{self.agent_type.value.upper()}_{timestamp}_{random_id}"
        
        cache_breaker = f"[Agent Session: {agent_session}]\n[Processing: {self.agent_type.value}]\n[Timestamp: {datetime.now().isoformat()}]\n\n"
        
        return cache_breaker + text
    
    async def process(self, input_text: str, model: str = 'gpt-4o-mini') -> AgentResult:
        """
        Process resume text and extract section-specific data
        
        Args:
            input_text: Resume text (can be full resume or chunked section)
            model: OpenAI model to use
            
        Returns:
            AgentResult with extracted data and metadata
        """
        start_time = start_timing()
        
        try:
            input_length = len(input_text)
            logger.info(f"🤖 {self.agent_type.value.title()} Agent: Starting extraction... (Input: {input_length} chars)")
            
            # Prepare the prompt with cache busting
            user_prompt = self._add_cache_variation(
                f"Extract {self.agent_type.value} information from this resume:\n\n{input_text}"
            )
            
            # Make OpenAI API call
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": user_prompt}
                ],
                tools=[{"type": "function", "function": self.schema}],
                tool_choice={"type": "function", "function": {"name": self.schema["name"]}},
                max_tokens=8192,
                temperature=0.1
            )
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Log cache analysis
            log_cache_analysis(response, self.agent_type.value)
            
            # Parse the response
            tool_call_arguments = response.choices[0].message.tool_calls[0].function.arguments
            extracted_data = json.loads(tool_call_arguments)
            
            # Clean bullet points if needed
            cleaned_data = self._clean_extracted_data(extracted_data)
            
            logger.info(f"✅ {self.agent_type.value.title()} Agent: Extraction successful ({processing_time:.2f}s)")
            
            return AgentResult(
                agent_type=self.agent_type,
                data=cleaned_data,
                processing_time=processing_time,
                success=True
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ {self.agent_type.value.title()} Agent: JSON parsing error - {e}")
            return self._create_error_result(start_time, f"JSON parsing failed: {e}")
            
        except Exception as e:
            logger.error(f"❌ {self.agent_type.value.title()} Agent: Processing failed - {e}")
            return self._create_error_result(start_time, str(e))
    
    def _clean_extracted_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean bullet points and format extracted data"""
        if self.agent_type == AgentType.SUMMARY and data.get('professionalSummary'):
            data['professionalSummary'] = [strip_bullet_prefix(item) for item in data['professionalSummary']]
            
            if data.get('summarySections'):
                for section in data['summarySections']:
                    if section.get('content'):
                        section['content'] = [strip_bullet_prefix(item) for item in section['content']]
        
        elif self.agent_type == AgentType.EXPERIENCE and data.get('employmentHistory'):
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
    
    def _create_error_result(self, start_time: datetime, error_message: str) -> AgentResult:
        """Create an error result"""
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return AgentResult(
            agent_type=self.agent_type,
            data={},
            processing_time=processing_time,
            success=False,
            error_message=error_message
        )

class MultiAgentResumeProcessor:
    """
    Orchestrates multiple specialized agents for parallel resume processing
    """
    
    def __init__(self, client: AsyncOpenAI):
        self.client = client
        
    async def process_resume_with_agents(
        self, 
        raw_text: str, 
        model: str = 'gpt-4o-mini'
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process resume using multiple specialized agents in parallel with intelligent chunking
        
        Args:
            raw_text: Complete resume text
            model: OpenAI model to use
            
        Yields:
            Streaming updates with progress and results
        """
        logger.info("🚀 Multi-Agent Resume Processing: Starting parallel extraction...")
        
        yield {
            'type': 'agent_processing_start',
            'message': 'Initializing specialized AI agents...',
            'progress': 15,
            'timestamp': datetime.now().isoformat()
        }
        
        # 🔥 NEW: Chunk the resume first
        yield {
            'type': 'chunking_start',
            'message': 'Chunking resume into sections...',
            'progress': 18,
            'timestamp': datetime.now().isoformat()
        }
        
        from .chunk_resume import chunk_resume_from_bold_headings
        sections = chunk_resume_from_bold_headings(raw_text)
        
        # Check if chunking was successful
        if 'error' in sections:
            logger.warning(f"⚠️ Chunking failed: {sections['error']} - Using full resume for all agents")
            sections = {}
        
        logger.info(f"📊 Chunked sections available: {list(sections.keys())}")
        
        yield {
            'type': 'chunking_complete',
            'message': f'Resume chunked into {len(sections)} sections. Preparing agent inputs...',
            'progress': 22,
            'sections': list(sections.keys()),
            'timestamp': datetime.now().isoformat()
        }
        
        # Create all agents
        agents = [
            ResumeAgent(self.client, AgentType.HEADER),
            ResumeAgent(self.client, AgentType.SUMMARY),
            ResumeAgent(self.client, AgentType.EXPERIENCE),
            ResumeAgent(self.client, AgentType.EDUCATION),
            ResumeAgent(self.client, AgentType.SKILLS),
            ResumeAgent(self.client, AgentType.CERTIFICATIONS)
        ]
        
        yield {
            'type': 'agents_created',
            'message': f'Created {len(agents)} specialized agents. Preparing intelligent inputs...',
            'progress': 25,
            'agents': [agent.agent_type.value for agent in agents],
            'timestamp': datetime.now().isoformat()
        }
        
        # 🎯 NEW: Prepare intelligent inputs for each agent
        agent_inputs = self._prepare_agent_inputs(agents, sections, raw_text)
        
        # Create strategy summary for user feedback
        strategy_summary = {}
        for agent_type, strategy in agent_inputs['strategy'].items():
            if strategy == 'chunked_section':
                strategy_summary[agent_type] = '✅ Using chunked section'
            elif strategy == 'chunked_with_context':
                strategy_summary[agent_type] = '✅ Using chunked section + context'
            elif strategy == 'full_resume_always':
                strategy_summary[agent_type] = '🔍 Using full resume (certification rule)'
            elif strategy == 'full_resume_fallback':
                strategy_summary[agent_type] = '⚠️ Using full resume (section missing)'
        
        yield {
            'type': 'inputs_prepared',
            'message': 'Agent inputs prepared with intelligent chunking. Starting parallel processing...',
            'progress': 28,
            'input_strategy': agent_inputs['strategy'],
            'strategy_summary': strategy_summary,
            'timestamp': datetime.now().isoformat()
        }
        
        # Process all agents in parallel with intelligent inputs
        try:
            agent_tasks = [
                agent.process(agent_inputs['inputs'][agent.agent_type], model) 
                for agent in agents
            ]
            results = await asyncio.gather(*agent_tasks, return_exceptions=True)
            
            yield {
                'type': 'agents_completed',
                'message': 'All agents completed processing. Combining results...',
                'progress': 75,
                'timestamp': datetime.now().isoformat()
            }
            
            # Process results
            successful_results = []
            failed_agents = []
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Agent task failed with exception: {result}")
                    failed_agents.append(str(result))
                    continue
                    
                if result.success:
                    successful_results.append(result)
                else:
                    failed_agents.append(f"{result.agent_type.value}: {result.error_message}")
            
            # Combine results into final structure
            combined_data = self._combine_agent_results(successful_results)
            
            # Report any failures
            if failed_agents:
                logger.warning(f"Some agents failed: {failed_agents}")
                yield {
                    'type': 'partial_failure',
                    'message': f'Warning: {len(failed_agents)} agents failed, but processing continued',
                    'failed_agents': failed_agents,
                    'timestamp': datetime.now().isoformat()
                }
            
            yield {
                'type': 'final_data',
                'data': combined_data,
                'message': 'Multi-agent processing completed successfully!',
                'progress': 95,
                'processing_summary': {
                    'successful_agents': len(successful_results),
                    'failed_agents': len(failed_agents)
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Multi-agent processing failed: {e}")
            yield {
                'type': 'error',
                'message': f'Multi-agent processing failed: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
    
    def _prepare_agent_inputs(self, agents: List[ResumeAgent], sections: Dict[str, str], raw_text: str) -> Dict[str, Any]:
        """
        Prepare intelligent inputs for each agent based on chunked sections
        
        Args:
            agents: List of resume agents
            sections: Chunked resume sections
            raw_text: Complete resume text as fallback
            
        Returns:
            Dictionary with agent inputs and strategy information
        """
        agent_inputs = {}
        strategy = {}
        
        # Section mapping for agents
        section_mapping = {
            AgentType.HEADER: 'header',
            AgentType.SUMMARY: 'summary', 
            AgentType.EXPERIENCE: 'experience',
            AgentType.EDUCATION: 'education',
            AgentType.SKILLS: 'skills',
            AgentType.CERTIFICATIONS: 'certifications'  # Special case - always gets full resume
        }
        
        for agent in agents:
            agent_type = agent.agent_type
            section_key = section_mapping[agent_type]
            
            # 🎯 CERTIFICATION AGENT: Always gets full resume
            if agent_type == AgentType.CERTIFICATIONS:
                agent_inputs[agent_type] = raw_text
                strategy[agent_type.value] = 'full_resume_always'
                logger.info(f"🔍 {agent_type.value.title()} Agent: Using full resume (certification rule)")
                continue
            
            # 🎯 OTHER AGENTS: Use chunked section if available, otherwise full resume
            if section_key in sections and sections[section_key] and sections[section_key].strip():
                # Use chunked section
                chunked_content = sections[section_key].strip()
                
                # For header agent, also include some context from the beginning
                if agent_type == AgentType.HEADER:
                    # Include first 1000 characters for better context
                    context_text = raw_text[:1000]
                    agent_inputs[agent_type] = f"{context_text}\n\n--- HEADER SECTION ---\n{chunked_content}"
                    strategy[agent_type.value] = 'chunked_with_context'
                else:
                    agent_inputs[agent_type] = chunked_content
                    strategy[agent_type.value] = 'chunked_section'
                
                logger.info(f"✅ {agent_type.value.title()} Agent: Using chunked section ({len(chunked_content)} chars)")
            else:
                # Fallback to full resume
                agent_inputs[agent_type] = raw_text
                strategy[agent_type.value] = 'full_resume_fallback'
                logger.info(f"⚠️ {agent_type.value.title()} Agent: Section missing/empty, using full resume")
        
        return {
            'inputs': agent_inputs,
            'strategy': strategy
        }
    
    def _combine_agent_results(self, results: List[AgentResult]) -> Dict[str, Any]:
        """
        Combine results from all agents into the expected resume structure
        
        Args:
            results: List of successful agent results
            
        Returns:
            Combined resume data in original format
        """
        # Initialize with default structure
        combined_data = {
            'name': '',
            'title': '',
            'requisitionNumber': '',
            'professionalSummary': [],
            'summarySections': [],
            'subsections': [],  # For compatibility
            'employmentHistory': [],
            'education': [],
            'certifications': [],
            'technicalSkills': {},
            'skillCategories': []
        }
        
        # Merge data from each agent
        for result in results:
            agent_data = result.data
            
            if result.agent_type == AgentType.HEADER:
                combined_data.update({
                    'name': agent_data.get('name', ''),
                    'title': agent_data.get('title', ''),
                    'requisitionNumber': agent_data.get('requisitionNumber', '')
                })
                
            elif result.agent_type == AgentType.SUMMARY:
                combined_data.update({
                    'professionalSummary': agent_data.get('professionalSummary', []),
                    'summarySections': agent_data.get('summarySections', [])
                })
                # For compatibility
                combined_data['subsections'] = combined_data['summarySections']
                
            elif result.agent_type == AgentType.EXPERIENCE:
                combined_data['employmentHistory'] = agent_data.get('employmentHistory', [])
                
            elif result.agent_type == AgentType.EDUCATION:
                combined_data['education'] = agent_data.get('education', [])
                
            elif result.agent_type == AgentType.SKILLS:
                combined_data.update({
                    'technicalSkills': agent_data.get('technicalSkills', {}),
                    'skillCategories': agent_data.get('skillCategories', [])
                })
                
            elif result.agent_type == AgentType.CERTIFICATIONS:
                combined_data['certifications'] = agent_data.get('certifications', [])
        
        logger.info(f"✅ Combined data from {len(results)} agents successfully")
        return combined_data