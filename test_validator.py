import unittest

# Assuming the commit_message_validator function is defined in a module called validator
from main import commit_message_validator


class TestCommitMessageValidator(unittest.TestCase):

    def test_valid_commit_message_with_description(self):
        commit_msg = "feat: Add new feature"
        result = commit_message_validator.run(commit_msg)
        self.assertTrue(result['is_valid'])
        self.assertEqual(len(result['errors']), 0)
        self.assertEqual(len(result['suggestions']), 0)

    def test_valid_commit_message_with_scope(self):
        commit_msg = "fix(core): Correct minor typos in code"
        result = commit_message_validator.run(commit_msg)
        self.assertTrue(result['is_valid'])
        self.assertEqual(len(result['errors']), 0)
        self.assertEqual(len(result['suggestions']), 0)

    def test_valid_commit_message_with_breaking_change_footer(self):
        commit_msg = """chore!: Drop support for Node 6

BREAKING CHANGE: use JavaScript features not available in Node 6.
"""
        result = commit_message_validator.run(commit_msg)
        self.assertTrue(result['is_valid'])
        self.assertEqual(len(result['errors']), 0)
        self.assertEqual(len(result['suggestions']), 0)

    def test_valid_commit_message_with_bang_breaking_change(self):
        commit_msg = "refactor!: Drop support for Node 6"
        result = commit_message_validator.run(commit_msg)
        self.assertTrue(result['is_valid'])
        self.assertEqual(len(result['errors']), 0)
        self.assertEqual(len(result['suggestions']), 0)

    def test_valid_commit_message_with_footer(self):
        commit_msg = """fix: Prevent racing of requests

Reviewed-by: Z
Refs: #123
"""
        result = commit_message_validator.run(commit_msg)
        self.assertTrue(result['is_valid'])
        self.assertEqual(len(result['errors']), 0)
        self.assertEqual(len(result['suggestions']), 0)

    def test_invalid_commit_message_missing_type(self):
        commit_msg = "add new feature"
        result = commit_message_validator.run(commit_msg)
        self.assertFalse(result['is_valid'])
        self.assertIn(
            "Subject line must contain a type, optional scope, and description separated by a colon and space.",
            result['errors'])

    def test_invalid_commit_message_missing_description(self):
        commit_msg = "feat:"
        result = commit_message_validator.run(commit_msg)
        self.assertFalse(result['is_valid'])
        self.assertIn("Missing commit description. Please provide a clear and concise summary of the changes made in the commit. The description should briefly explain the purpose and impact of the modifications.", result['errors'])

    def test_valid_commit_message_with_docs_type(self):
        commit_msg = "docs: Update README.md"
        result = commit_message_validator.run(commit_msg)
        self.assertTrue(result['is_valid'])
        self.assertEqual(len(result['errors']), 0)
        self.assertEqual(len(result['suggestions']), 0)

    def test_valid_commit_message_with_multiple_paragraphs_in_body(self):
        commit_msg = """fix: Prevent racing of requests

    Introduce a request id and a reference to latest request. Dismiss
    incoming responses other than from latest request.

    Remove timeouts which were used to mitigate the racing issue but are
    obsolete now.
    """
        result = commit_message_validator.run(commit_msg)
        self.assertTrue(result['is_valid'])
        self.assertEqual(len(result['errors']), 0)
        self.assertEqual(len(result['suggestions']), 0)

    def test_valid_commit_message_with_body_and_footer(self):
        commit_msg = """feat(search): Add filtering options to search API

- Introduce `filter` query parameter to search endpoint
- Implement filtering functionality in `SearchService`
- Update API documentation with details on using `filter`

The search API now supports filtering results based on user-specified
criteria. This enhancement improves the flexibility and usability of 
the search feature.

Closes #123"""
        result = commit_message_validator.run(commit_msg)
        self.assertTrue(result['is_valid'])
        self.assertEqual(len(result['errors']), 0)
        self.assertEqual(len(result['suggestions']), 0)

    def test_valid_commit_message_with_multiline_body(self):
        commit_msg = """fix(authentication): Resolve user login issues

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

Fixes #789"""
        result = commit_message_validator.run(commit_msg)
        self.assertTrue(result['is_valid'])
        self.assertEqual(len(result['errors']), 0)
        self.assertEqual(len(result['suggestions']), 0)

    def test_valid_commit_message_with_issue_reference(self):
        commit_msg = """feat(search): Add filtering options to search API

- Introduce `filter` query parameter to search endpoint
- Implement filtering functionality in `SearchService`
- Update API documentation with details on using `filter`

The search API now supports filtering results based on user-specified
criteria. This enhancement improves the flexibility and usability of
the search feature.

Closes #123"""
        result = commit_message_validator.run(commit_msg)
        self.assertTrue(result['is_valid'])
        self.assertEqual(len(result['errors']), 0)
        self.assertEqual(len(result['suggestions']), 0)

    def test_invalid_commit_message_invalid_type(self):
        commit_msg = "invalid: add new feature"
        result = commit_message_validator.run(commit_msg)
        self.assertFalse(result['is_valid'])
        self.assertIn(
            "Invalid commit type 'invalid'. Commit type must be one of the allowed types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert.",
            result['errors'])

    def test_invalid_commit_message_invalid_scope_format(self):
        commit_msg = "feat(InvalidScope): add new feature"
        result = commit_message_validator.run(commit_msg)
        self.assertFalse(result['is_valid'])
        self.assertIn("Scope should be lowercase.", result['errors'])

    def test_invalid_commit_message_subject_line_over_50_chars(self):
        commit_msg = "feat: this is a subject line that is over 50 characters long and should trigger an error"
        result = commit_message_validator.run(commit_msg)
        self.assertFalse(result['is_valid'])
        self.assertIn("Subject line should be 50 characters or less, currently it is 88 characters. Consider rephrasing the subject to be more concise whilst still capturing the essence of the changes.", result['errors'])

    def test_valid_commit_message_with_valid_type_scope_and_description(self):
        commit_msg = "feat(search): Add filtering options to search API"
        result = commit_message_validator.run(commit_msg)
        assert result["is_valid"] == True
        assert len(result["errors"]) == 0
        assert len(result["suggestions"]) == 0

    def test_valid_commit_message_with_breaking_change_indicator(self):
        commit_msg = "feat(search): Add filtering options to search API!\n\nBREAKING CHANGE: Updated the search algorithm"
        result = commit_message_validator.run(commit_msg)
        assert result["is_valid"] == True
        assert len(result["errors"]) == 0
        assert len(result["suggestions"]) == 0

    def test_valid_commit_message_with_short_subject_line(self):
        commit_msg = "feat(search): Add filtering options"
        result = commit_message_validator.run(commit_msg)
        assert result["is_valid"] == True
        assert len(result["errors"]) == 0
        assert len(result["suggestions"]) == 0

    def test_valid_commit_message_with_blank_line_between_subject_and_body(self):
        commit_msg = "feat(search): Add filtering options to search API\n\nThe search API now supports filtering results based on user-specified\ncriteria."
        result = commit_message_validator.run(commit_msg)
        assert result["is_valid"] == True
        assert len(result["errors"]) == 0
        assert len(result["suggestions"]) == 0

    def test_commit_message_with_empty_subject_line(self):
        commit_msg = ""
        result = commit_message_validator.run(commit_msg)
        assert result["is_valid"] == False
        assert len(result["errors"]) == 1
        assert len(result["suggestions"]) == 0

    def test_commit_message_with_missing_commit_type(self):
        commit_msg = ": Add filtering options to search API"
        result = commit_message_validator.run(commit_msg)
        assert result["is_valid"] == False
        assert len(result["errors"]) == 1
        assert len(result["suggestions"]) == 0

    def test_commit_message_with_non_lowercase_type(self):
        commit_msg = "Feat(search): Add filtering options to search API"
        result = commit_message_validator.run(commit_msg)
        assert result["is_valid"] == False
        assert len(result["errors"]) == 2
        assert len(result["suggestions"]) == 0

    def test_commit_message_with_non_lowercase_scope(self):
        commit_msg = "feat(Search): Add filtering options to search API"
        result = commit_message_validator.run(commit_msg)
        assert result["is_valid"] == False
        assert len(result["errors"]) == 1
        assert len(result["suggestions"]) == 0

    def test_commit_message_with_invalid_commit_type(self):
        commit_msg = "feature(search): Add filtering options to search API"
        result = commit_message_validator.run(commit_msg)
        assert result["is_valid"] == False
        assert len(result["errors"]) == 2
        assert len(result["suggestions"]) == 0

    # Add a test where the subject line is 50 characters long
    def test_commit_message_with_49_char_subject_line(self):
        commit_msg = "feat(search): Add filtering options to search API"
        result = commit_message_validator.run(commit_msg)
        assert result["is_valid"] == True
        assert len(result["errors"]) == 0
        assert len(result["suggestions"]) == 0


if __name__ == '__main__':
    unittest.main()
