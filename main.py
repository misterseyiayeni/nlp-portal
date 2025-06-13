import boto3
import json
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="GenAI NLP API")

# Environment configuration
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "translation_log")

# Initialize AWS clients
bedrock_runtime = boto3.client("bedrock-runtime", region_name=AWS_REGION)
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE)

# Request models for various endpoints
class TranslationRequest(BaseModel):
    text: str
    target_language: str

class TextRequest(BaseModel):
    text: str

# New ChatRequest model replacing the earlier QA model.
class ChatRequest(BaseModel):
    prompt: str

# Helper for invoking the Bedrock model
def invoke_model_with_prompt(prompt: str) -> str:
    body = json.dumps({
        "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
        "max_tokens_to_sample": 500,
    })
    try:
        response = bedrock_runtime.invoke_model(
            body=body,
            modelId="anthropic.claude-v2",
            accept="application/json",
            contentType="application/json"
        )
        result = json.loads(response.get("body").read())
        return result.get("completion", "").strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model invocation failed: {e}")

# Helper for logging to DynamoDB
def log_request(module: str, record: dict):
    try:
        record["module"] = module
        table.put_item(Item=record)
    except Exception as e:
        print(f"Error logging {module} request to DynamoDB: {e}")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "GenAI NLP API is running"}

@app.post("/translate")
def translate_text(request: TranslationRequest):
    prompt = f"Translate the following text to {request.target_language}: {request.text}"
    translated_text = invoke_model_with_prompt(prompt)

    log_request("translation", {
        "requestId": str(hash(request.text)),
        "original_text": request.text,
        "target_language": request.target_language,
        "result": translated_text
    })

    return {"translated_text": translated_text}

@app.post("/sentiment")
def sentiment_analysis(request: TextRequest):
    prompt = f"Analyze the sentiment of the following text and describe whether it is positive, negative, or neutral: {request.text}"
    sentiment = invoke_model_with_prompt(prompt)

    log_request("sentiment", {
        "requestId": str(hash(request.text)),
        "original_text": request.text,
        "result": sentiment
    })
    
    return {"sentiment": sentiment}

# New chat prompt endpoint replacing the earlier QA endpoint.
@app.post("/chat")
def chat_prompt(request: ChatRequest):
    # Here, we treat the incoming prompt as the entire conversational input.
    chat_response = invoke_model_with_prompt(request.prompt)
    
    log_request("chat", {
        "requestId": str(hash(request.prompt)),
        "prompt": request.prompt,
        "result": chat_response
    })
    
    return {"chat_response": chat_response}

@app.post("/ner")
def named_entity_recognition(request: TextRequest):
    prompt = f"Identify and list the named entities (such as people, organizations, locations) in the following text: {request.text}"
    entities = invoke_model_with_prompt(prompt)

    log_request("ner", {
        "requestId": str(hash(request.text)),
        "original_text": request.text,
        "result": entities
    })
    
    return {"named_entities": entities}

@app.post("/summarize")
def text_summarization(request: TextRequest):
    prompt = f"Summarize the following text concisely: {request.text}"
    summary = invoke_model_with_prompt(prompt)

    log_request("summarization", {
        "requestId": str(hash(request.text)),
        "original_text": request.text,
        "result": summary
    })
    
    return {"summary": summary}

