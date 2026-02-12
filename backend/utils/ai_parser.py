import os
import logging
from datetime import datetime
from typing import Dict, Any, AsyncGenerator
from openai import AsyncOpenAI

from .chunk_resume import chunk_resume_from_bold_headings

logger = logging.getLogger(__name__)

api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    logger.error("❌ OPENAI_API_KEY environment variable is not set")
    raise ValueError("OPENAI_API_KEY environment variable is not set")
logger.info(f"✅ OpenAI API key found: {api_key[:10]}...")
client = AsyncOpenAI(api_key=api_key)

async def stream_resume_processing(extracted_text: str) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Simple resume processing - just loading and final result
    """
    logger.info('Starting resume processing...')
    
    try:
        # Use multi-agent processing
        from .resume_agents import MultiAgentResumeProcessor
        
        processor = MultiAgentResumeProcessor(client)
        
        # Process resume and get final result
        async for update in processor.process_resume_with_agents(extracted_text):
            # Only yield the final data, ignore all progress events
            if update.get('type') == 'final_data':
                yield update
                return

    except Exception as error:
        logger.error(f'❌ Resume processing error: {error}')
        yield {
            'type': 'error',
            'message': f'Resume processing error: {error}',
            'timestamp': datetime.now().isoformat()
        }






