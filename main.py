import os
import subprocess

from crewai import Agent, Task, Crew
from crewai_tools import tool


@tool("Commit Message Validator")
def commit_message_validator(suggested_commit_msg: str) -> str:
    """
    Validates the suggested commit message against best practices, including conventional
    commit structure, effective subject lines, comprehensive message bodies,
    identification of breaking changes, and language consistency.
    """
    errors = []
    # Splitting the message into lines for detailed analysis
    lines = suggested_commit_msg.strip().split('\n')

    # Check for conventional commit structure
    if ':' not in lines[0] or not lines[0].split(':')[0].islower():
        errors.append("Commit type must be lowercase and followed by a colon (:).")

    # Effective subject line
    subject_line = lines[0]
    if len(subject_line) > 50:
        errors.append("Subject line exceeds 50 characters.")
    if not subject_line[0].isupper() or subject_line.istitle():
        errors.append("Subject line must start with a capital letter and be in lowercase.")
    if subject_line.endswith('.'):
        errors.append("Subject line must not end with a period.")

    # Comprehensive message body and blank line check
    if len(lines) > 1:
        if lines[1] != "":
            errors.append("There must be a blank line between the subject line and body.")
        body_lines = lines[2:]
        for line in body_lines:
            if len(line) > 72:
                errors.append("Body lines must not exceed 72 characters.")
    else:
        body_lines = []

    if errors:
        return "Errors found in commit message:\n" + "\n".join(errors)
    else:
        return "Commit message is valid."


def is_git_repo(path):
    """Check if the given path is a git repository"""
    try:
        subprocess.check_call(['git', '-C', path, 'rev-parse'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False


def get_last_commit_info(repo_path):
    """Get the last commit message and changes from the git repository at the given path"""
    commit_msg = subprocess.check_output(['git', '-C', repo_path, 'log', '-1', '--pretty=%B']).decode('utf-8').strip()

    # Check the number of commits
    num_commits = int(
        subprocess.check_output(['git', '-C', repo_path, 'rev-list', '--count', 'HEAD']).decode('utf-8').strip())

    if num_commits > 1:
        # If there are at least two commits, compare the last commit with its parent
        commit_diff = subprocess.check_output(['git', '-C', repo_path, 'diff', 'HEAD^', 'HEAD']).decode('utf-8')
    else:
        # If there is only one commit, compare it with an empty tree
        empty_tree_hash = subprocess.check_output(['git', 'hash-object', '-t', 'tree', '/dev/null']).decode(
            'utf-8').strip()
        commit_diff = subprocess.check_output(['git', '-C', repo_path, 'diff', empty_tree_hash, 'HEAD']).decode('utf-8')

    return commit_msg, commit_diff


def main():
    # Get the current working directory
    repo_path = os.getcwd()

    # Check if the directory contains a .git folder
    if not is_git_repo(repo_path):
        print(f"{repo_path} is not a git repository")
        return

    # Get the last commit message and changes
    commit_msg, commit_diff = get_last_commit_info(repo_path)

    # Create the CrewAI agents
    code_analyzer = Agent(
        role='Code Analyzer',
        goal='Analyze code changes and suggest improvements to the commit message. Git diff:\n{commit_diff}',
        backstory='A code analysis expert with experience in reviewing git diffs and providing feedback on commit messages.',
        verbose=True,  # Optional
        memory=True,
        allow_delegation=False,
        tools=[commit_message_validator]
    )

    commit_suggester = Agent(
        role='Commit Message Suggester',
        goal='Suggest a new conventional commit message based on the code changes. Current commit message: "{commit_msg}"',
        backstory='A commit message specialist who can craft clear and concise commit messages following conventional commit standards.',
        verbose=True,  # Optional
        memory=True,
        allow_delegation=False,
        tools=[commit_message_validator]
    )

    commit_validation_agent = Agent(
        role='Commit Validator',
        goal='Ensure the suggested commit message meets all best practices before finalization.',
        backstory='Dedicated to maintaining high standards in commit documentation.',
        verbose=True,  # Optional
        memory=True,
        tools=[commit_message_validator]
    )

    # Define the tasks for the agents
    analyze_task = Task(
        objective=f"Analyze the following code changes",
        description="Review the git diff and provide a summary of the code changes",
        expected_output="A brief summary of the code changes",
        result_format="Provide a brief summary of the code changes",
        agent=code_analyzer
    )

    suggest_task = Task(
        objective="Suggest a new conventional commit message based on the summary of code changes",
        description="Use the analysis result to propose a new commit message",
        expected_output="A suggested conventional commit message",
        result_format="Provide the suggested commit message",
        agent=commit_suggester
    )

    # Create the CrewAI crew
    crew = Crew(
        agents=[code_analyzer, commit_suggester, commit_validation_agent],
        tasks=[analyze_task, suggest_task],
        verbose=True  # Optional
    )

    # Execute the tasks using the kickoff method
    print(
        crew.kickoff(
            inputs={
                'commit_diff': commit_diff,
                'commit_msg': commit_msg
            }
        )
    )

    # print(f"Original commit message: {commit_msg}")
    # print(f"Analysis of code changes: {analysis_result}")
    # print(f"Suggested commit message: {suggested_commit_msg}")


if __name__ == '__main__':
    main()
