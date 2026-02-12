"""
FastAPI Resume Builder Backend - AWS Lambda Version
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
import os
import tempfile
from pathlib import Path
import logging
import json
from datetime import datetime

from utils.file_parser import extract_text_from_file
from utils.ai_parser import stream_resume_processing

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Resume Builder API", version="1.0.0")

# Note: CORS is handled by AWS Lambda Function URLs automatically

@app.get("/")
async def root():
    return {"message": "Resume Builder API is running"}

@app.post("/api/stream-resume-processing")
async def stream_resume_processing_endpoint(file: UploadFile = File(...)):
    """Stream resume processing endpoint - Function URL with 5 minute timeout"""
    try:
        logger.info(f"Processing file: {file.filename} ({file.content_type})")

        temp_file_path = None
        suffix = Path(file.filename).suffix
        content = await file.read()
        # ADD THIS: Check if file content is valid
        if not content:
            logger.error("❌ File content is empty")
            raise HTTPException(status_code=400, detail="File is empty")
        logger.info(f"✅ File read successfully: {len(content)} bytes")
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(content)
        logger.info(f"✅ Temp file created: {temp_file_path}")
        try:
            # Extract text from file - no timeout worries with Function URLs!
            logger.info("🔄 Starting text extraction...")
            extracted_text = extract_text_from_file(temp_file_path)
            logger.info(f"✅ Text extracted: {len(extracted_text)} characters")
            extracted_text = extract_text_from_file(temp_file_path)


            async def generate_stream():
                try:
                    async for chunk in stream_resume_processing(extracted_text):
                        # Ensure proper SSE format with explicit flush
                        event_data = json.dumps(chunk, ensure_ascii=False)
                        yield f"data: {event_data}\n\n"
                        
                    # Send completion signal
                    yield "data: [DONE]\n\n"
                except Exception as stream_error:
                    logger.error(f"❌ Streaming error: {stream_error}")
                    error_data = json.dumps({
                        'type': 'error',
                        'message': f'Streaming error: {str(stream_error)}',
                        'timestamp': datetime.now().isoformat()
                    })
                    yield f"data: {error_data}\n\n"

            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"  # Disable nginx buffering
                }
            )
        finally:
            try:
                os.unlink(temp_file_path)
            except Exception as cleanup_error:
                logger.error(f"❌ Error cleaning up temp file: {cleanup_error}")

    except Exception as e:
        logger.error(f"❌ Error in streaming processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))
