Feature: Tri Mode - Parallel Multi-Provider Queries
  As a user
  I want to query all providers in parallel
  So that I can compare responses from multiple models

  Background:
    Given the AiTril web server is running
    And I have a WebSocket connection

  Scenario: Query all three providers in parallel
    When I send a tri mode request with prompt "Count to 3"
    Then I should receive a "trilam_started" event
    And the event should list 3 providers
    And I should receive "agent_started" events for all providers
    And I should receive "agent_completed" events for "openai"
    And I should receive "agent_completed" events for "anthropic"
    And I should receive "agent_completed" events for "gemini"
    And I should receive a "trilam_completed" event

  Scenario: All providers respond independently
    When I send a tri mode request with prompt "Say your name"
    Then each provider should return a unique response
    And all responses should be received within 15 seconds
    And no provider should block others
