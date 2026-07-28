import sys, os, json
sys.path.insert(0, "backend")

from modules.whisper_module import WhisperModule

m = WhisperModule(model_size="tiny")
result = m.transcribe_video("test_whisper_input.mp4")

print("Lingua:", result["language"])
print("Duracao:", result["duration"])
print("Palavras:", len(result["words"]))
print("Segmentos:", len(result["segments"]))
if result["words"]:
    print("Primeiras 5:", result["words"][:5])
else:
    print("Nenhuma palavra detectada (sinal sem fala - esperado)")
print("Formato do resultado OK")
