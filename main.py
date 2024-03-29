import os
import subprocess

from crewai import Agent, Task, Crew
from crewai_tools import tool


@tool("Commit Message Validator")
def commit_message_validator(suggested_commit_msg: str) -> str:
    """
    Validates the suggested commit message against best practices for conventional commits,
    focusing on structure, subject line, body comprehensiveness, and breaking changes.
    """
    errors = []
    suggestions = []
    lines = suggested_commit_msg.strip().split('\n')

    if ':' not in lines[0]:
        errors.append("Commit message must include a type followed by a colon (:).")
    else:
        type_part, description_part = lines[0].split(':', 1)
        if not type_part.islower():
            errors.append("Commit type must be lowercase.")
        valid_types = ['feat', 'fix', 'docs', 'style', 'refactor', 'perf', 'test', 'build', 'ci', 'chore', 'revert', 'security']
        if type_part not in valid_types:
            errors.append(f"Invalid commit type. Valid types are: {', '.join(valid_types)}")
        description_part = description_part.strip()
        if description_part and not description_part[0].isupper():
            suggestions.append("Commit description should start with a capital letter.")

    # Validate subject line length
    subject_line = lines[0]
    if len(subject_line) > 50:
        suggestions.append("Subject line should be limited to around 50 characters where possible.")
    if subject_line.endswith('.'):
        suggestions.append("Subject line should not end with a full stop.")

    # Validate blank line between subject and body, if body exists
    if len(lines) > 1 and lines[1] != "":
        errors.append("There must be a blank line between the subject line and body.")

    # Validate body lines length
    body_lines = lines[2:]
    for line in body_lines:
        if len(line) > 72:
            suggestions.append(f"Consider breaking up the line '{line}' to improve readability.")

    # Validate breaking changes format
    breaking_changes = [line for line in body_lines if line.startswith("BREAKING CHANGE:")]
    if breaking_changes:
        for change in breaking_changes:
            if not change.startswith("BREAKING CHANGE:"):
                errors.append("Breaking changes must start with 'BREAKING CHANGE:' for emphasis.")
    else:
        footer_lines = lines[-2:]
        breaking_changes_footer = [line for line in footer_lines if line.startswith("BREAKING CHANGE:")]
        if breaking_changes_footer:
            for change in breaking_changes_footer:
                if not change.startswith("BREAKING CHANGE:"):
                    errors.append("Breaking changes in the footer must start with 'BREAKING CHANGE:' for emphasis.")

    if errors:
        return f"Errors found in commit message:\n" + "\n".join(errors) + "\n\nSuggestions:\n" + "\n".join(suggestions)
    elif suggestions:
        return f"Commit message is valid, but consider the following suggestions:\n" + "\n".join(suggestions)
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
    try:
        commit_msg = subprocess.check_output(['git', '-C', repo_path, 'log', '-1', '--pretty=%B']).decode('utf-8').strip()
        commit_diff = subprocess.check_output(['git', '-C', repo_path, 'diff', 'HEAD^', 'HEAD']).decode('utf-8')
        return commit_msg, commit_diff
    except subprocess.CalledProcessError as e:
        print(f"Error getting last commit info: {str(e)}")
        return None, None


def main(repo_path=None, dry_run=False):
    if repo_path is None:
        repo_path = os.getcwd()

    if not is_git_repo(repo_path):
        print(f"{repo_path} is not a git repository")
        return

    commit_msg, commit_diff = get_last_commit_info(repo_path)
    if commit_msg is None or commit_diff is None:
        print("Unable to get last commit information")
        return

    code_analyzer = Agent(
        role='Code Analyzer',
        goal='Analyze code changes and summarize them. Git diff:\n{commit_diff}',
        backstory='A code analysis expert with experience in reviewing git diffs.',
        verbose=True,
        memory=True,
        allow_delegation=False
    )

    commit_suggester = Agent(
        role='Commit Message Suggester',
        goal='Suggest a concise yet descriptive conventional commit message based on the code changes. The message should follow this format: <type>[optional scope]: <description>\n\nType should be one of feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert, security.\nOptional scope can specify the area of the code affected.\nDescription should be capitalized and not end with a period.',
        backstory='A seasoned developer experienced in writing clear and concise commit messages following conventional commit standards.',
        verbose=True,
        memory=True,
        allow_delegation=False,
        tools=[commit_message_validator]
    )

    commit_validation_agent = Agent(
        role='Commit Validator',
        goal='Ensure the suggested commit message follows best practices. Provide actionable suggestions if needed.',
        backstory='Dedicated to maintaining high standards in commit documentation.',
        verbose=True,
        memory=True,
        tools=[commit_message_validator]
    )

    analyze_task = Task(
        objective=f"Summarize the code changes",
        description="Review the git diff and provide a brief summary of the changes",
        expected_output="A concise summary of the code changes",
        result_format="Provide a clear and concise summary of the code changes",
        agent=code_analyzer
    )

    suggest_task = Task(
        objective="Suggest a conventional commit message based on the summary of code changes",
        description="Use the analysis result to propose a commit message that follows conventional commit standards",
        expected_output="A suggested conventional commit message",
        result_format="Provide a clear and concise commit message that adheres to conventional commit guidelines",
        agent=commit_suggester
    )

    crew = Crew(
        agents=[code_analyzer, commit_suggester, commit_validation_agent],
        tasks=[analyze_task, suggest_task],
        verbose=True
    )

    result = crew.kickoff(
        inputs={
            'commit_diff': commit_diff,
            'commit_msg': commit_msg
        }
    )

    # Parse the result string to extract the task outputs
    analysis_result = ""
    suggested_commit_msg = ""
    for line in result.split("\n"):
        if line.startswith("[Code Analyzer] Task output:"):
            analysis_result = line.split("[Code Analyzer] Task output:")[1].strip()
        elif line.startswith("[Commit Message Suggester] Task output:"):
            suggested_commit_msg = line.split("[Commit Message Suggester] Task output:")[1].strip()

    print(f"Original commit message: {commit_msg}")
    print(f"Analysis of code changes: {analysis_result}")
    print(f"Suggested commit message: {suggested_commit_msg}")

    if not dry_run:
        # Amend the last commit with the suggested message
        subprocess.check_call(['git', '-C', repo_path, 'commit', '--amend', '-m', suggested_commit_msg])
        print("Last commit message has been updated.")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Analyze and suggest improvements to the last git commit message.")
    parser.add_argument('--repo-path', help="Path to the git repository (default: current working directory)")
    parser.add_argument('--dry-run', action='store_true', help="Perform a dry run without modifying the commit message")
    args = parser.parse_args()

    main(repo_path=args.repo_path, dry_run=args.dry_run)