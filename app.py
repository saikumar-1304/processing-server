import json
import os
import threading
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from S3Uploader import S3UploadQueue
from chatgpt import ChatGPT

load_dotenv()

app = FastAPI()

# CORS middleware for allowing cross-origin requests (optional)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key = os.getenv('API_KEY')
chatgpt_instance = ChatGPT(api_key=api_key)

UPLOAD_FOLDER = 'Data'  # Base folder to upload files
s3 = S3UploadQueue()


def build_prompt(content):
    combined_prompt = (f"""Given {content}, 
        This is a lecture transcript. Summarize the class for a student for revision.
        Generate 10 questions based on the lecture, ranging from easy, medium, hard, to application-based questions, 
        each with 4 options and one correct answer.
        Format the output as JSON, with keys "summary" and "quiz_questions". 
        The "quiz_questions" key should contain an array of objects, each with keys "question", "answer", and "options".
        Example format: 
        {{
            "summary": "<summary of content>", 
            "quiz_questions": [
                {{
                    "question": "<question>",
                    "answer": "<correct answer index from options>",
                    "options": ["option1", "option2", "option3", "option4"]
                }}
            ]
        }}""")

    return combined_prompt


def format_quiz(quiz_data):
    formatted_text = ""
    answers = []

    # Process quiz questions
    for i, question_data in enumerate(quiz_data):
        formatted_text += f"Question {i + 1}: {question_data['question']}\n"

        # Assign letters a, b, c, d to options
        for index, opt in enumerate(question_data['options']):
            letter = chr(97 + index)  # Convert index to letter (a, b, c, d)
            formatted_text += f"     {letter}: {opt}\n"

        # Determine the correct answer letter (0-indexed to a, b, c, d)
        correct_letter = chr(97 + int(question_data['answer']))  # Use the index directly
        answers.append(
            f"  {i + 1}. {correct_letter}: {question_data['options'][int(question_data['answer'])]}\n"
        )  # Use the correct option
        formatted_text += "\n"

    # Add answers section
    formatted_text += "Answers:\n"
    formatted_text += "".join(answers) + "\n"

    return formatted_text


@app.post("/process_files")
async def process_files(
        school: str = Form(...),
        subject: str = Form(...),
        file: UploadFile = File(...)
):
    # Check if file is provided
    if not file.filename:
        raise HTTPException(status_code=400, detail="No selected file")

    timestamp = '_'.join(file.filename.split("_")[:2])

    # Check if school and subject are provided
    if not school or not subject:
        raise HTTPException(status_code=400, detail="School and subject are required")

    school_folder = os.path.join(UPLOAD_FOLDER, school)
    subject_folder = os.path.join(school_folder, subject)
    timestamp_folder = os.path.join(subject_folder, timestamp)
    os.makedirs(timestamp_folder, exist_ok=True)

    file_path = os.path.join(timestamp_folder, file.filename)

    # Save the uploaded file
    with open(file_path, 'wb') as f:
        f.write(await file.read())

    with open(file_path, 'r') as tf:
        file_content = tf.read()

    combined_prompt = build_prompt(file_content)
    response = json.loads(chatgpt_instance.chat_with_gpt(combined_prompt))

    summary = response['summary']
    quiz = response['quiz_questions']

    with open(os.path.join(timestamp_folder, f"{timestamp}_summary.txt"), 'w') as f:
        f.write(summary)

    with open(os.path.join(timestamp_folder, f"{timestamp}_quiz.txt"), 'w') as f:
        f.write(format_quiz(quiz))

    s3.add_to_queue(school=school, subject=subject, local_directory=timestamp_folder)

    return JSONResponse(content=response)


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=5000)
