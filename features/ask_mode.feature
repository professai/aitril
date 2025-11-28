Feature: Ask Mode - Single Provider Queries
  As a user
  I want to query a single LLM provider
  So that I can get responses from a specific model

  Background:
    Given the AiTril web server is running
    And I have a WebSocket connection

  Scenario: Query OpenAI provider
    When I send an ask mode request to "openai" with prompt "What is 2+2?"
    Then I should receive a "message_received" event
    And I should receive an "agent_started" event for "openai"
    And I should receive "agent_chunk" events
    And I should receive an "agent_completed" event with a response

  Scenario: Query Anthropic provider
    When I send an ask mode request to "anthropic" with prompt "What is 2+2?"
    Then I should receive a "message_received" event
    And I should receive an "agent_started" event for "anthropic"
    And I should receive "agent_chunk" events
    And I should receive an "agent_completed" event with a response

  Scenario: Query Gemini provider
    When I send an ask mode request to "gemini" with prompt "What is 2+2?"
    Then I should receive a "message_received" event
    And I should receive an "agent_started" event for "gemini"
    And I should receive "agent_chunk" events
    And I should receive an "agent_completed" event with a response
