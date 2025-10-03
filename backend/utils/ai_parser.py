import os
import re
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, AsyncGenerator
from openai import AsyncOpenAI



from .chunk_resume import chunk_resume_from_bold_headings

logger = logging.getLogger(__name__)

api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

client = AsyncOpenAI(api_key=api_key)

async def stream_resume_processing(extracted_text: str) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Stream resume processing with multi-agent system
    """
    logger.info('\n=== STREAMING AI PARSER: Starting multi-agent resume processing ===')
    
    try:
        # Send initial connection test
        yield {
            'type': 'connection',
            'message': 'Connected to resume processing service',
            'progress': 5,
            'timestamp': datetime.now().isoformat()
        }
        
        yield {
            'type': 'progress',
            'message': 'Analyzing resume structure...',
            'progress': 10,
            'timestamp': datetime.now().isoformat()
        }

        sections = chunk_resume_from_bold_headings(extracted_text)
        logger.info(f'Sections detected: {list(sections.keys())}')

        # Use multi-agent processing
        from .resume_agents import MultiAgentResumeProcessor
        
        processor = MultiAgentResumeProcessor(client)
        
        # Stream multi-agent processing
        async for update in processor.process_resume_with_agents(extracted_text):
            yield update
            
            # If we get final data, we're done
            if update.get('type') == 'final_data':
                return

    except Exception as error:
        logger.error(f'❌ Multi-agent processing error: {error}')
        yield {
            'type': 'error',
            'message': f'Multi-agent processing error: {error}',
            'timestamp': datetime.now().isoformat()
        }






