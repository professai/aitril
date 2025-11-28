Feature: AiTril CLI Interface
  As a developer
  I want to use AiTril from the command line
  So that I can query LLM providers without a web interface

  Background:
    Given I have AiTril CLI installed
    And API keys are configured in environment

  Scenario: Check CLI version
    When I run "aitril --version"
    Then the output should contain "0.0.22"
    And the exit code should be 0

  Scenario: CLI help command
    When I run "aitril --help"
    Then the output should contain "Multi-LLM orchestration"
    And the output should contain "ask"
    And the output should contain "tri"
    And the output should contain "build"
    And the exit code should be 0

  Scenario: Ask mode with GPT
    When I run "aitril ask --provider gpt 'What is 2+2? Answer with just the number.'"
    Then the output should contain a numeric answer
    And the exit code should be 0

  Scenario: Ask mode with Claude
    When I run "aitril ask --provider claude 'What is 2+2? Answer with just the number.'"
    Then the output should contain a numeric answer
    And the exit code should be 0

  Scenario: Ask mode with Gemini
    When I run "aitril ask --provider gemini 'What is 2+2? Answer with just the number.'"
    Then the output should contain a numeric answer
    And the exit code should be 0

  Scenario: Tri mode with all providers
    When I run "aitril tri 'Say hello in one word'"
    Then the output should contain "OpenAI" or "GPT"
    And the output should contain "Anthropic" or "Claude"
    And the output should contain "Gemini" or "Google"
    And the exit code should be 0

  Scenario: Tri mode shows multiple responses
    When I run "aitril tri 'Count to 3'"
    Then I should see responses from 3 providers
    And the output should contain "TRI-LAM RESULTS"
    And the exit code should be 0

  Scenario: Build mode creates code
    When I run "aitril build 'Create a hello world function'"
    Then the output should contain "Planning"
    And the output should contain "Implementation"
    And the output should contain "Review"
    And the exit code should be 0

  Scenario: Invalid provider shows error
    When I run "aitril ask --provider invalid 'test'"
    Then the output should contain "error" or "invalid"
    And the exit code should not be 0

  Scenario: Missing prompt shows error
    When I run "aitril ask --provider gpt"
    Then the output should contain "required" or "error"
    And the exit code should not be 0
