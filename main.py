import os
import re
import subprocess
import textwrap
import time
from pathlib import Path

from crewai import Agent, Task, Crew, Process
from crewai_tools import tool
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

# Load environment variables from .env file
dotenv_path = Path('.env')
load_dotenv(dotenv_path=dotenv_path)

# High-performance model for complex tasks, most expensive
claude_llm_high = ChatAnthropic(model="claude-3-opus-20240229", temperature=0)

# Balanced model for general use, moderately priced
claude_llm_medium = ChatAnthropic(model="claude-3-sonnet-20240229", temperature=0)

# Fastest model for quick responses, most affordable
claude_llm_low = ChatAnthropic(model="claude-3-haiku-20240307", temperature=0)

openai_llm = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0)


def wrap_text(input_text, width=72):
    """Wrap text to a specified width, handling bullet points with indentation"""
    intput_lines = input_text.split('\n')
    wrapped_lines = []
    for line in intput_lines:
        if line.startswith('- '):  # This is a bullet point
            wrapped_lines.append('\n'.join(textwrap.wrap(line, width, subsequent_indent='  ')))
        else:  # This is not a bullet point
            wrapped_lines.append('\n'.join(textwrap.wrap(line, width)))
    return '\n'.join(wrapped_lines)


@tool("Conventional Commit Message Validator")
def commit_message_validator(suggested_commit_msg: str) -> dict[str, list[str] | bool]:
    """
    Use this tool to validate that a suggested commit message follows the Conventional Commits 1.0.0 specification.

    The Conventional Commits specification is a lightweight convention on top of commit messages, which provides an easy set of rules for creating an explicit commit history. Enforcing this convention leads to more readable messages that are easier to follow when looking through the project history.

    The tool checks the message for:
    - Proper structure of type[(scope)][!]: description
    - Allowed types (feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert)
    - Valid scope format (lowercase, parentheses)
    - Breaking changes indicator (!)
    - Subject line max length (50 chars) and formatting (lowercase type, scope, and bang)
    - Blank line between subject and body
    - Line lengths in body and footers (max 72 chars)
    - Formatting of breaking changes (BREAKING CHANGE: description)
    - Formatting of footers (TOKEN: value or KEYWORD #123)

    The tool returns a dictionary with:
    - errors: a list of any structural errors found
    - suggestions: a list of suggestions for improving the message
    - is_valid: a boolean indicating if the message is fully valid

    Use this tool to ensure your commit messages are consistent and informative according to the Conventional Commits 1.0.0 spec.
    See https://www.conventionalcommits.org/en/v1.0.0/ for full specification details.
    """
    errors = []
    suggestions = []
    valid_types = ['feat', 'fix', 'docs', 'style', 'refactor', 'perf', 'test', 'build', 'ci', 'chore', 'revert']
    lines = suggested_commit_msg.strip().split('\n')
    subject_line = lines[0]
    stripped_lines = [line.strip() for line in lines]

    breaking_change_footer_present = False
    has_blank_line = any(line.strip() == "" for line in stripped_lines[1:])

    # Validate subject line
    if not subject_line:
        errors.append("Subject line cannot be empty.")
    elif ':' not in subject_line:
        errors.append(
            "Subject line must contain a type, optional scope, and description separated by a colon and space.")
    else:
        type_scope, _, description = subject_line.partition(':')
        type_scope = type_scope.replace('!', '')  # Remove '!' for further processing
        type_part, _, scope_part = type_scope.partition('(')
        scope_part = scope_part[:-1] if scope_part.endswith(')') else scope_part  # Remove closing parenthesis

        def add_error(error_message: str):
            errors.append(error_message)

        # Validate type and scope
        if not type_part:
            add_error("Missing or invalid commit type. Commit type must be one of the allowed types.")
        elif not type_part.islower():
            add_error("Type should be lowercase.")

        if scope_part and not scope_part.islower():
            add_error("Scope should be lowercase.")

        if type_part and type_part not in valid_types:
            add_error(
                f"Invalid commit type '{type_part}'. Commit type must be one of the allowed types: {', '.join(valid_types)}.")

        # Validate description
        if not description.strip():
            add_error(
                "Missing commit description. Please provide a clear and concise summary of the changes made in the commit. The description should briefly explain the purpose and impact of the modifications.")

        if len(subject_line) > 50:
            add_error(
                f"Subject line should be 50 characters or less, currently it is {len(subject_line)} characters. Consider rephrasing the subject to be more concise whilst still capturing the essence of the changes.")

        if description.strip() and not description.strip()[0].isupper():
            suggestions.append(
                "Consider capitalising the first letter of the commit subject for consistency and readability, unless it starts with a lowercase identifier or acronym.")

        if description.strip() and not description.strip().startswith(
                ('Add', 'Update', 'Remove', 'Fix', 'Refactor', 'Improve', 'Use', 'Replace',
                 'Modify', 'Rename', 'Move', 'Change', 'Enhance', 'Drop', 'Correct', 'Prevent', 'Resolve')):
            suggestions.append(
                "Consider using the imperative mood in the commit subject, e.g., 'Add feature' instead of 'Added feature'. This convention helps maintain a consistent style and tone across commit messages.")

    # Validate body and footer
    footer_section = False
    for line in stripped_lines[1:]:
        if not footer_section and line == "":
            footer_section = True
            continue

        if footer_section:
            if line.startswith("BREAKING CHANGE:"):
                breaking_change_footer_present = True
            elif line.startswith(("BREAKING-CHANGE:", "BREAKING_CHANGE:")):
                errors.append("Breaking change footer should start with 'BREAKING CHANGE:'.")
            elif ": " in line:
                footer_parts = line.split(": ", 1)
                if not footer_parts[0].isupper() or " " in footer_parts[0]:
                    if footer_parts[0] not in ["Reviewed-by", "Refs", "Closes"]:
                        errors.append(
                            f"Invalid footer format: {line}. Footer token should be uppercase, not contain spaces, and be one of the allowed tokens: 'BREAKING CHANGE', 'Reviewed-by', 'Refs', or 'Closes'."
                        )
            elif line.strip() and line.startswith(("Reviewed-by:", "Refs:", "Closes:")):
                # Valid footer format
                pass
            else:
                # Not a footer, treat as part of the body
                footer_section = False

        if len(line) > 72:
            wrapped_line = textwrap.wrap(line, 72)
            errors.append(
                f"Line '{line}' exceeds the recommended maximum length of 72 characters. To improve readability and maintainability, consider rewording the line to be more concise or breaking it into multiple shorter lines.")
            suggestions.append(
                f"Consider breaking up '{line}' into multiple lines like the following:\n{wrapped_line}")

    if not has_blank_line and len(stripped_lines) > 1:
        errors.append(
            "Missing blank line between the subject line and the commit body/footers. To adhere to the Conventional Commits specification, please add a blank line after the subject to visually separate it from the detailed commit description and any footers.")

    if breaking_change_footer_present:
        suggestions = [s for s in suggestions if not s.startswith("Consider adding a BREAKING CHANGE footer")]

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


def pull_commit_messages_text_file(repo_path):
    """Check if commit_messages.txt exists and was changed in the last 10 minutes. If so, return its content."""
    try:
        commit_messages_file = os.path.join(repo_path, 'commit_messages.txt')
        if os.path.exists(commit_messages_file):
            last_modified = os.path.getmtime(commit_messages_file)
            current_time = time.time()
            if current_time - last_modified < 600:
                with open(commit_messages_file, 'r') as f:
                    return f.read()
    except Exception as e:
        print(f"Error reading commit_messages.txt: {str(e)}")
    return None


def get_examples():
    """Return a string containing example commit messages"""
    example1 = """Commit: 7058c7a9cc55e2dd81ea53ac401c98d48b394418
    ```md
    feat(search): Add filtering options to search API

- Introduce `filter` query parameter to search endpoint
- Implement filtering functionality in `SearchService`
- Update API documentation with details on using `filter`

The search API now supports filtering results based on user-specified
criteria. This enhancement improves the flexibility and usability of 
the search feature.
```"""

    example2 = """Commit: 4d7a1c0b2e8f6h5i9j3k7l1m2n3o4p5q6r7s8t9u
```md
fix(authentication): Resolve user login issues

- Investigate and fix the bug causing intermittent login failures
- Improve error handling and logging in the authentication module
- Implement retry mechanism for failed login attempts

The authentication process was occasionally failing due to a race
condition in the user validation logic. The issue has been resolved by
adding proper synchronisation and error handling.

Additionally, a retry mechanism has been introduced to handle transient
network failures during login. If a login attempt fails due to a
network issue, the system will automatically retry the request up to
three times before reporting an error to the user.

These changes significantly improve the reliability and user experience
of the login feature.
```"""

    example3 = """Commit: 7058c7a9cc55e2dd81ea53ac401c98d48b394418
```md
feat(search): Add filtering options to search API

- Introduce `filter` query parameter to search endpoint
- Implement filtering functionality in `SearchService`
- Update API documentation with details on using `filter`

The search API now supports filtering results based on user-specified
criteria. This enhancement improves the flexibility and usability of
the search feature.
```"""

    return "Example 1:\n" + example1 + "\n\nExample 2:\n" + example2 + "\n\nExample 3:\n" + example3 + "\n\n"


def get_last_commit_info(repo_path):
    """Get the last commit message, diff, and commit_messages.txt content from the git repository at the given path"""
    try:
        commit_msg = subprocess.check_output(['git', '-C', repo_path, 'log', '-1', '--pretty=%B']).decode(
            'utf-8').strip()
        commit_diff = subprocess.check_output(['git', '-C', repo_path, 'diff', '-U5', 'HEAD^', 'HEAD']).decode('utf-8')

        commit_messages = pull_commit_messages_text_file(repo_path)

        return commit_msg, commit_diff, commit_messages
    except subprocess.CalledProcessError as e:
        print(f"Error getting last commit info: {str(e)}")
        return None, None, None


def main(repo_path=None, dry_run=False):
    """Main function to analyze and suggest improvements to the last git commit message"""
    if repo_path is None:
        repo_path = os.getcwd()

    if not is_git_repo(repo_path):
        print(f"{repo_path} is not a git repository")
        return

    commit_msg, commit_diff, commit_messages = get_last_commit_info(repo_path)
    if commit_msg is None or commit_diff is None:
        print("Unable to get last commit information")
        return

    examples = get_examples()

    # Initialize agents for code analysis, commit message suggestion, validation, and finalization
    first_code_analyser = Agent(
        role='First Code Change Summariser',
        goal="""
            Summarise key aspects of code changes

            Provide a concise, high-level overview of the modifications, focusing on:
            - Added functionality
            - Removed functionality
            - Updated functionality

            Capture the essence of the changes in a clear and focused summary. Ensure conventions for UK English spelling, grammar, punctuation, and terminology are followed.

            As the First Code Change Summariser, your role is to provide an initial summary of the code changes using the OpenAI GPT-4 model. This summary will be complemented by the Second Code Change Summariser, which uses the Claude model for a different perspective.

            -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
            Current Commit Message:
            {commit_msg}
            -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
            Commit Diff:
            {commit_diff}
            -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-""",
        backstory="You excel at distilling complex code changes into their core components. Your summaries are renowned for their clarity and ability to convey the heart of the modifications.",
        verbose=True,
        memory=True,
        allow_delegation=False,
        llm=openai_llm,
        max_iterations=1,
    )

    second_code_analyser = Agent(
        role='Second Code Change Summariser',
        goal="""
            Summarise key aspects of code changes

            Provide a concise, high-level overview of the modifications, focusing on:
            - Added functionality
            - Removed functionality
            - Updated functionality

            Capture the essence of the changes in a clear and focused summary. Ensure conventions for UK English spelling, grammar, punctuation, and terminology are followed.

            As the Second Code Change Summariser, your role is to provide a complementary summary of the code changes using the Claude model. This summary will offer a different perspective to the First Code Change Summariser, which uses the OpenAI GPT-4 model.

            -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
            Current Commit Message:
            {commit_msg}
            -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
            Commit Diff:
            {commit_diff}
            -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-""",
        backstory="You excel at distilling complex code changes into their core components. Your summaries are renowned for their clarity and ability to convey the heart of the modifications.",
        verbose=True,
        memory=True,
        allow_delegation=False,
        llm=claude_llm_medium,
        max_iterations=1,
    )

    commit_suggester = Agent(
        role='Conventional Commit Craftsperson',
        goal="""
        Compose a descriptive conventional commit message based on the provided code changes and current commit message.

        Responsibilities:
        - Generate a commit message that adheres to the conventional commit format: `<type>[scope]: <description>`
        - Ensure the message encapsulates the nature of the change in the type and description
        - Provide a concise yet informative summary in the subject line
        - Elaborate further in the body when needed, explaining the 'why' and 'how'
        - Maintain a line length of around 72 characters for readability
        - If the commit message is found to be invalid by the validator, revise the message based on the feedback and try again
        - Ensure conventions for UK English spelling, grammar, punctuation, and terminology are followed

        The commit message should accurately reflect the changes and enhance the project's commit history.

        -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-  
        Current Commit Message:
        {commit_msg}
        -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
        Commit Diff:  
        {commit_diff}
        -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
        Best Practice examples:
        {examples}
        -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-""",
        backstory='With a deep understanding of clean commit practices, you craft messages that not only describe the change but also provide valuable context for future developers.',
        verbose=True,
        memory=True,
        allow_delegation=True,
        tools=[commit_message_validator],
        llm=claude_llm_low
    )

    external_validator = Agent(
        role='External Best Practices Validator',
        goal="""
        Validate the commit message to ensure it follows conventional commit message standards, aligns with external best practices, and adheres to team-specific conventions.

        Responsibilities:
        - Review the suggested commit message to ensure compliance with conventional commit standards
        - Use the commit_message_validator tool to validate the message structure and format
        - Verify alignment with external coding and documentation best practices
        - Suggest enhancements for clarity, impact, and alignment with project goals
        - Flag any issues or deviations from team-specific conventions
        - Provide clear and actionable feedback for improving the commit message if it doesn't meet the standards
        - If the message is invalid, suggest specific changes that can be made to make it valid
        - Ensure conventions for UK English spelling, grammar, punctuation, and terminology are followed

        This agent serves as a quality assurance step to validate the suggested commit message, ensuring it meets all necessary standards and conventions.

        -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-  
        Current Commit Message:
        {commit_msg}
        -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
        Commit Diff:  
        {commit_diff}
        -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
        Best Practice examples:
        {examples}
        -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-""",
        backstory='As the guardian of coding standards, best practices, and commit message integrity, you ensure every commit message not only meets conventional standards but also embodies the team\'s ethos and project\'s quality benchmarks.',
        verbose=True,
        memory=True,
        allow_delegation=True,
        tools=[commit_message_validator],
        llm=claude_llm_medium
    )

    finaliser = Agent(
        role='Commit Message Finaliser',
        goal="""
            Review the suggested commit message, incorporating feedback from code analysis, initial suggestion, and external validation tasks. 

            Responsibilities:
            - Ensure the final message adheres to conventional commit standards
            - Incorporate all necessary details and context from the code analysis
            - Address any issues or suggestions raised during the external validation step
            - Maintain clarity, conciseness, and compliance with all guidelines
            - If the message is found to be invalid, work with the other agents to iteratively improve it until it meets all standards
            - Maintain clarity, conciseness, and compliance with all guidelines
            - Use UK English spelling, grammar, punctuation, and terminology

            As the Commit Message Finaliser, your role is to review and incorporate feedback from previous steps to produce a polished, high-quality commit message that meets all project standards.
            """,
        backstory='As the Commit Message Finaliser, you take pride in delivering commit messages that meet the highest standards. You work tirelessly with the other agents, iterating and refining the message until it is deemed valid and in full compliance with all guidelines. Your meticulous attention to detail ensures that every commit message adheres to UK English conventions and project-specific requirements.',
        verbose=True,
        memory=True,
        allow_delegation=True,
        llm=claude_llm_high
    )

    # Define tasks for each agent
    first_analyse_task = Task(
        description="Provide a high-level overview of the modifications, focusing on added, removed, or updated functionality",
        expected_output="A clear and concise summary of the essential code changes, capturing the core of the modifications",
        agent=first_code_analyser,
    )

    second_analyse_task = Task(
        description="Provide a high-level overview of the modifications, focusing on added, removed, or updated functionality",
        expected_output="A clear and concise summary of the essential code changes, capturing the core of the modifications",
        agent=second_code_analyser,
    )

    suggest_task = Task(
        description="Craft a commit message encapsulating the change type and key details, adhering to conventional commit standards",
        expected_output="A well-structured conventional commit message that accurately reflects the changes and enhances the project's commit history",
        agent=commit_suggester,
    )

    external_validation_task = Task(
        description="""
        Validate and enhance the commit message to ensure it aligns with conventional commit standards, external best practices, and team conventions.
        Provide detailed feedback on the commit message structure, suggesting improvements and flagging any potential issues.
        """,
        expected_output="""
        Feedback on the commit message with validation against conventional commit standards, suggestions for enhancements, and flags for potential issues.
        """,
        agent=external_validator,
    )

    finalizing_task = Task(
        description="""
            Finalise the commit message, ensuring it is the best representation of the changes made. Adjust based on earlier analyses and validations, ensuring clarity, compliance, and conciseness.
            """,
        expected_output="""
            The final, ready-to-use commit message that adheres to all project and conventional standards.
            """,
        agent=finaliser,
    )

    # Initialize the crew with agents, tasks, and process configuration
    crew = Crew(
        tasks=[first_analyse_task, second_analyse_task, suggest_task, external_validation_task, finalizing_task],
        agents=[first_code_analyser, second_code_analyser, commit_suggester, external_validator, finaliser],
        manager_llm=ChatOpenAI(model="gpt-4"),
        process=Process.sequential,
        verbose=True,
        share_crew=False,
    )

    # Kick off the crew with the necessary inputs
    result = crew.kickoff(
        inputs={
            'commit_diff': commit_diff,
            'commit_msg': commit_msg,
            'commit_messages': commit_messages,
            'examples': examples.strip(),
        },
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
