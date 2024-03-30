# ConventionalCommitAgent

ConventionalCommitAgent is a Python-based application that utilizes the CrewAI library and various other dependencies to
perform specific tasks related to enforcing and validating conventional commit messages in a Git repository. It helps
maintain a consistent and structured commit history by ensuring that commit messages adhere to
the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification.

## Features

- Validates commit messages against the Conventional Commits specification
- Provides suggestions for improving commit messages
- Integrates with Git repositories to analyze commit history

## Prerequisites

- Docker
- Docker Compose

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/MarjovanLier/ConventionalCommitAgent.git
   ```

2. Navigate to the project directory:
   cd ConventionalCommitAgent

3. Build and run the Docker container using Docker Compose:
   docker-compose up --build
   This command will build the Docker image based on the provided Dockerfile and start the container.

## Contributing

Contributions to ConventionalCommitAgent are welcome! If you encounter any issues or have suggestions for improvements,
please open an issue on the [GitHub repository](https://github.com/MarjovanLier/ConventionalCommitAgent/issues).
When contributing to this project, please follow the existing code style and conventions. Make sure to write tests for
any new features or bug fixes. Before submitting a pull request, ensure that all tests pass and the code is properly
formatted.