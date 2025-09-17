import os
from mangum import Mangum
from main import app
#keep this for local testing
os.environ.setdefault('AWS_LAMBDA_FUNCTION_NAME', 'resume-builder-api')

handler = Mangum(app, lifespan="off")

def lambda_handler(event, context):
    
    return handler(event, context)
