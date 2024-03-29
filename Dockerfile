FROM python:3.10

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install CrewAI
RUN pip install crewai

# Copy the application code
COPY . .

# Set the entrypoint command
#ENTRYPOINT ["python", "main.py"]

# Command to keep the container running
CMD ["tail", "-f", "/dev/null"]