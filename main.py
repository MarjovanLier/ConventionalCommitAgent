import os
import re
import subprocess

from crewai import Agent, Task, Crew
from crewai_tools import tool


@tool("Commit Message Validator")
def commit_message_validator(suggested_commit_msg: str) -> dict[str, list[str] | bool]:
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
        if '(' in type_part and ')' in type_part:
            type_part, scope_part = type_part.split('(', 1)
        if not type_part.islower():
            errors.append("Commit type must be lowercase.")
        valid_types = ['feat', 'fix', 'docs', 'style', 'refactor', 'perf', 'test', 'build', 'ci', 'chore', 'revert',
                       'security']
        if type_part not in valid_types:
            errors.append(f"Invalid commit type '{type_part}'. Valid types are: {', '.join(valid_types)}")
        description_part = description_part.strip()
        if description_part and not description_part[0].isupper():
            suggestions.append("Commit description should start with a capital letter.")

    # Validate subject line length
    subject_line = lines[0]
    if len(subject_line) > 50:
        suggestions.append("Subject line should be limited to around 50 characters where possible.")
    if subject_line.endswith('.'):
        suggestions.append("Subject line should not end with a full stop.")

    # Validate body existence
    if len(lines) < 3:
        errors.append("Commit message should have a body providing more details about the changes.")

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

    return {
        "errors": errors,
        "suggestions": suggestions,
        "is_valid": len(errors) == 0
    }


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
        commit_msg = subprocess.check_output(['git', '-C', repo_path, 'log', '-1', '--pretty=%B']).decode(
            'utf-8').strip()
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

    code_analyser = Agent(
        role='Code Change Summariser',
        goal="""
            Concisely summarise the key aspects of the code modifications. Highlight added, removed, 
            or updated functionality. Aim for a high-level overview that captures the essence.
            -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
            Old Commit Message:
            {commit_msg}
            -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
            Commit Diff:
            {commit_diff}
            -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
            """,
        backstory="You excel at distilling complex code changes into their core components. Your summaries are renowned for their clarity and ability to convey the heart of the modifications.",
        verbose=True,
        memory=True,
        allow_delegation=False
    )

    commit_suggester = Agent(
        role='Conventional Commit Craftsperson',
        goal="""
            Compose a clear and descriptive commit message adhering to the conventional commit format.
            Encapsulate the nature of the change in the type and description. Provide a concise yet 
            informative summary in the subject line. When needed, elaborate further in the body.
            -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
            Old Commit Message:
            {commit_msg}
            -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
            Commit Diff:
            {commit_diff}
            -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
            """,
        backstory='With a deep understanding of clean commit practices, you craft messages that not only describe the change but also provide valuable context for future developers.',
        verbose=True,
        memory=True,
        allow_delegation=False,
        tools=[commit_message_validator]
    )

    analyse_task = Task(
        objective=f"Summarise key aspects of the code changes",
        description="Provide a high-level overview of the modifications, focusing on added, removed, or updated functionality",
        expected_output="A clear and concise summary of the essential code changes",
        result_format="A focused summary that captures the core of the code modifications",
        agent=code_analyser,
    )

    suggest_task = Task(
        objective="Compose a descriptive conventional commit message",
        description="Craft a commit message encapsulating the change type and key details, adhering to conventional commit standards",
        expected_output="A well-structured conventional commit message accurately reflecting the changes",
        result_format="A thoughtfully composed commit message that enhances the project's commit history",
        agent=commit_suggester,
    )

    crew = Crew(
        agents=[code_analyser, commit_suggester],
        tasks=[analyse_task, suggest_task],
        verbose=True
    )

    result = crew.kickoff(
        inputs={
            'commit_diff': commit_diff,
            'commit_msg': commit_msg
        }
    )

    print("-=-=-=-=-=-=-=-")
    print(result)
    print("-=-=-=-=-=-=-=-")

    # Parse the result string to extract the task outputs
    analysis_result = ""
    suggested_commit_msg = ""
    validation_result = ""
    lines = result.split("\n")
    for i in range(len(lines)):
        if lines[i].startswith("[Code Analyzer] Task output:"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("["):
                analysis_result += lines[j].strip() + " "
                j += 1
        elif lines[i].startswith("[Commit Message Suggester] Task output:"):
            suggested_commit_msg = lines[i + 1].strip().strip('"')
        elif lines[i].startswith("[Commit Validator] Task output:"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("["):
                validation_result += lines[j].strip() + " "
                j += 1

    # Extract the suggested commit message and validation result from the result string
    suggested_commit_msg_match = re.search(r'"(.*?)"', result)
    if suggested_commit_msg_match:
        suggested_commit_msg = suggested_commit_msg_match.group(1)

    validation_result_match = re.search(r'The commit message "(.*?)" is valid', result)
    if validation_result_match:
        validation_result = validation_result_match.group(0)

    print(f"Original commit message:\n{commit_msg}\n\n")
    print(f"Analysis of code changes:\n{analysis_result}\n\n")
    suggested_commit_msg = re.sub(r'\\n', '\n', suggested_commit_msg)
    print(f"Suggested commit message:\n{suggested_commit_msg}\n\n")
    print(f"Validation result:\n{validation_result}\n\n")

    if not dry_run and "is valid and follows the best practices" in validation_result:
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
