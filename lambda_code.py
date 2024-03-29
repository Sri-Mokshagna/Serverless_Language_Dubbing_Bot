import json
import boto3
import base64
import time
import http.client
import re
from datetime import datetime
from botocore.exceptions import ClientError

s3_client = boto3.client('s3')
translate_client = boto3.client('translate')
polly_client = boto3.client('polly')
transcribe_client = boto3.client('transcribe')

def translate_text(text, target_language):
    response = translate_client.translate_text(
        Text=text,
        SourceLanguageCode='auto',
        TargetLanguageCode=target_language
    )
    translated_text = response['TranslatedText']
    return translated_text

def initiate_transcription_job(bucket_name, mp3_file_name):
    job_name = f'transcription-job-{mp3_file_name}-{datetime.now().strftime("%Y%m%d%H%M%S")}'  # Generate a unique job name
    response = transcribe_client.start_transcription_job(
        TranscriptionJobName=job_name,
        LanguageCode='en-US',  
        MediaFormat='mp3',
        Media={
            'MediaFileUri': f's3://{bucket_name}/{mp3_file_name}'
        },
        OutputBucketName=bucket_name
    )
    return job_name

def check_transcription_job_status(job_name):
    response = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
    status = response['TranscriptionJob']['TranscriptionJobStatus']
    return status

def download_transcript(bucket_name, job_name):
    transcript_file_key = f'{job_name}.json'
    response = s3_client.get_object(Bucket=bucket_name, Key=transcript_file_key)
    json_data = json.loads(response['Body'].read().decode('utf-8'))
    return json_data


def send_telegram_message(chat_id, text):
    # Telegram bot token
    telegram_bot_token = "6929996860:AAG-bZmjNyKvp5aR2byVoywoA5b1V_AwS3E"

    # Telegram API endpoint
    host = "api.telegram.org"
    path = f"/bot{telegram_bot_token}/sendMessage"

    # Establish connection to Telegram API
    connection = http.client.HTTPSConnection(host)

    # Prepare request headers and payload
    headers = {"Content-type": "application/json"}
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    
    print("Sending message to Telegram...")
    # Send POST request to Telegram API
    connection.request("POST", path, body=json.dumps(payload), headers=headers)
    response = connection.getresponse()

    # Read and print the response
    response_data = response.read().decode("utf-8")
    print(response_data)

    # Close the connection
    connection.close()
def shorten_url(presigned_url):
    # Shorten the presigned URL manually
    parts = presigned_url.split("/")
    bucket_name = parts[2]
    object_key = "/".join(parts[3:])
    shortened_url = f"https://{bucket_name}.s3.amazonaws.com/{object_key}"
    return shortened_url

    return shortened_url
def lambda_handler(event, context):
    try:
        bucket_name = event['Records'][0]['s3']['bucket']['name']
        file_name = event['Records'][0]['s3']['object']['key']
        
        # Initiate transcription job
        job_name = initiate_transcription_job(bucket_name, file_name)
        
        # Poll for transcription job completion
        while True:
            status = check_transcription_job_status(job_name)
            if status == 'COMPLETED':
                break
            elif status == 'FAILED':
                raise Exception('Transcription job failed')
            time.sleep(10)  # Wait for 10 seconds before checking again
        
        # Download the transcript file
        transcript_data = download_transcript(bucket_name, job_name)
        print("Transcript data:", transcript_data)
        
        # Extract the transcript from JSON
        transcript = transcript_data['results']['transcripts'][0]['transcript']
        print("Transcript:", transcript)
        
        # Translate the transcript
        language_code_match = re.search(r'---([a-zA-Z]+)---', file_name)
        print("language")
        print(language_code_match)
        if language_code_match:
            language_code = language_code_match.group(1)
        else:
            language_code = 'en'
        target_language = language_code  
        print(target_language)
        translated_transcript = translate_text(transcript, target_language)
        
        # Synthesize speech using Amazon Polly
        voice_id = 'Joanna'  # Change this to your desired voice ID
        response = polly_client.synthesize_speech(Text=translated_transcript, OutputFormat='mp3', VoiceId=voice_id)
        
        # Upload the translated audio to a different bucket
        translated_bucket_name = "kluniversityyy"   
        translated_object_key = f"translated_audio.mp3"
        s3_client.put_object(Bucket=translated_bucket_name, Key=translated_object_key, Body=response['AudioStream'].read())
        
        pattern = r'(\d+)---'
        print("Event:", event)
        print("Object key:", file_name)
        # Search for the pattern in the input string
        match = re.search(pattern, file_name)
        presigned_url = s3_client.generate_presigned_url('get_object', Params={'Bucket': translated_bucket_name, 'Key': translated_object_key}, ExpiresIn=3600)
        shortened_url = shorten_url(presigned_url)
        if match:
            chat_id = match.group(1)
            send_telegram_message(chat_id, presigned_url)
        else:
            print("Chat ID not found in object key.")

        # Generate a presigned URL for the translated audio
        
        # Return a success response with the presigned URL
        response = {
            'statusCode': 200,
            'body': presigned_url
        }
    except Exception as e:
        # Return an error response if an exception occurs
        response = {
            'statusCode': 500,
            'body': f'Error: {str(e)}'
        }
    
    return response
