import pyttsx3

engine = pyttsx3.init()
engine.save_to_file("Hello..i need to book an appointment", "app.wav")
engine.runAndWait()

print("generated")

