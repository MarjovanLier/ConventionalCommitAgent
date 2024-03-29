import os
import subprocess
from crewai import Agent, Task, Crew

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
    num_commits = int(subprocess.check_output(['git', '-C', repo_path, 'rev-list', '--count', 'HEAD']).decode('utf-8').strip())

    if num_commits > 1:
        # If there are at least two commits, compare the last commit with its parent
        commit_diff = subprocess.check_output(['git', '-C', repo_path, 'diff', 'HEAD^', 'HEAD']).decode('utf-8')
    else:
        # If there is only one commit, compare it with an empty tree
        empty_tree_hash = subprocess.check_output(['git', 'hash-object', '-t', 'tree', '/dev/null']).decode('utf-8').strip()
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
        goal='Analyze code changes and suggest improvements to the commit message',
        backstory='A code analysis expert with experience in reviewing git diffs and providing feedback on commit messages.'
    )

    commit_suggester = Agent(
        role='Commit Message Suggester',
        goal='Suggest a new conventional commit message based on the code changes',
        backstory='A commit message specialist who can craft clear and concise commit messages following conventional commit standards.'
    )

    # Define the tasks for the agents
    analyze_task = Task(
        objective=f"Analyze the following code changes:\n{commit_diff}",
        description="Review the git diff and provide a summary of the code changes",
        expected_output="A brief summary of the code changes",
        result_format="Provide a brief summary of the code changes"
    )

    suggest_task = Task(
        objective=f"Suggest a new conventional commit message for the following changes:\n{{analyze_task_result}}",
        description="Propose a new commit message based on the summary of code changes",
        expected_output="A suggested conventional commit message",
        result_format="Provide the suggested commit message"
    )

    # Create the CrewAI crew
    crew = Crew(agents=[code_analyzer, commit_suggester])

    # Run the crew with the tasks
    crew.run([analyze_task, suggest_task])

    # Get the results
    analysis_result = analyze_task.result
    new_commit_msg = suggest_task.result

    print(f"Original commit message: {commit_msg}")
    print(f"Analysis of code changes: {analysis_result}")
    print(f"Suggested commit message: {new_commit_msg}")

if __name__ == '__main__':
    main()