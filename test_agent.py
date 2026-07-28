import sys, os, json
sys.path.insert(0, "backend")

from agents.transcription_agent import TranscriptionAgent
from agents.base_agent import AgentResult

agent = TranscriptionAgent(model_size="tiny")

task = {
    "project_assets": {
        "video_files": ["test_whisper_input.mp4"],
    }
}

result = agent.execute(task, None)

print("Success:", result.success)
print("Confidence:", result.confidence)
print("Logs:")
for l in result.logs:
    print("  ", l)
print("Limitations:", result.limitations)
print("Suggestions:", result.suggestions)

if result.data and "transcripts" in result.data:
    for t in result.data["transcripts"]:
        print("File:", t.get("file"))
        print("  Language:", t.get("language"))
        print("  Words:", len(t.get("words", [])))
        print("  Segments:", len(t.get("segments", [])))
