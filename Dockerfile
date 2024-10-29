# Use the prebuilt ostris/ai-toolkit image as the base
FROM ostris/aitoolkit:latest

# Set the working directory
WORKDIR /app

# Expose the default Gradio port for Koyeb
EXPOSE 7860

# Start the application, with dynamic port for Koyeb
CMD ["python", "run.py", "--listen", "0.0.0.0", "--port", "${PORT:-7860}"]
