# Video Study AI — Online Web App

This version is designed to be deployed as a browser-based website using Streamlit Community Cloud. Users open a URL; they do not install Python or Ollama on their own computer.

## What it does

- Upload video/audio files or provide a YouTube URL.
- Extract and split audio with FFmpeg.
- Transcribe speech using Groq's Whisper transcription API.
- Use a text model through Groq to generate quizzes, summaries, flashcards, notes, or other requested outputs.
- Download results as `.txt`.

## Free-use notes

The app is designed to use the provider's available free access where offered, but free quotas, model availability, file limits, and account requirements can change. You may need to create an account and provide your own API key. Do not publish your API key in source code or GitHub.

## Deploy it online (no local app install for users)

1. Create/sign in to a GitHub account: https://github.com/
2. Create a **new private repository** named `video-study-ai` (private is recommended while developing).
3. Upload these files to the repository root:
   - `app.py`
   - `requirements.txt`
   - `packages.txt`
4. Open Streamlit Community Cloud: https://share.streamlit.io/
5. Connect GitHub if prompted, then choose **Create app**.
6. Select your repository, branch (usually `main`), and main file path `app.py`.
7. Click **Deploy** and wait for the build to finish.
8. Open the app's website URL. In the sidebar, enter your Groq API key. Create/manage keys at https://console.groq.com/keys.

You may need to accept the current provider terms or have API access enabled before generation works.

## How to use

1. Open the hosted website.
2. Enter your Groq API key in the sidebar.
3. Upload a supported media file or choose YouTube URL and paste a link.
4. Write the task, e.g. "Create exactly 27 multiple-choice questions, four options each, answers and explanations."
5. Click **Generate study material**.
6. Download the result as a text file.

## Important limitations

- This MVP uses speech transcription. It does not yet analyze diagrams, slides, equations, or other video visuals.
- Long videos take longer to transcribe. The app splits audio into 8-minute segments.
- Very long transcripts may be truncated before text generation.
- YouTube retrieval can fail for restricted/private/age-gated videos or when YouTube changes its systems. Only process videos you have permission to access.
- Streamlit Community Cloud has resource and usage limits; the app can sleep or hit resource limits.
- The API provider receives audio for transcription and transcript text for generation. Do not use this demo for confidential videos.
- The app asks for the API key each session and does not deliberately save it. As with any hosted web app, use only a provider key you are comfortable using.
- This package has not been deployed to your accounts; you must complete the deployment steps to obtain your personal website URL.

## Troubleshooting

- **FFmpeg missing:** confirm `packages.txt` contains `ffmpeg` and redeploy.
- **Invalid API key:** create a fresh key in the provider console and enter it in the sidebar.
- **Rate limit/model not found:** review the provider console and choose a currently available text model in the sidebar.
- **YouTube URL fails:** try a different accessible video or upload a file you have permission to use.
- **Build fails:** open the app's deployment logs and share the error text for troubleshooting.
