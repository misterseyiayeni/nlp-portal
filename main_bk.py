import boto3
import json
import os
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# Get the AWS region and table name from environment variables
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'translation_log')

bedrock_runtime = boto3.client('bedrock-runtime', region_name=AWS_REGION)
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE)

class TranslationRequest(BaseModel):
    text: str
    target_language: str = "Spanish"

@app.get("/")
def read_root():
    return {"status": "ok", "message": "GenAI NLP API is running"}

@app.post("/translate")
def translate_text(request: TranslationRequest):
    prompt = f"Translate the following text to {request.target_language}: {request.text}"

    body = json.dumps({
        "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
        "max_tokens_to_sample": 500,
    })

    # Invoke Bedrock model
    response = bedrock_runtime.invoke_model(
        body=body, 
        modelId='anthropic.claude-v2',
        accept='application/json',
        contentType='application/json'
    )
    result = json.loads(response.get('body').read())
    translated_text = result.get('completion').strip()

    # Log to DynamoDB
    table.put_item(
        Item={
            'requestId': str(hash(request.text)), # Simple unique ID
            'original_text': request.text,
            'translated_text': translated_text,
            'target_language': request.target_language
        }
    )

    return {"translated_text": translated_text}
