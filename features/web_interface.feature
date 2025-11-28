Feature: AiTril Web Interface
  As a user of AiTril
  I want to access the web interface
  So that I can interact with multiple LLM providers

  Scenario: Access main web page
    Given the AiTril web server is running
    When I navigate to the home page
    Then I should see the AiTril interface
    And the page should load static assets

  Scenario: Health check endpoint
    Given the AiTril web server is running
    When I check the health endpoint
    Then the status should be "healthy"
    And the service name should be "aitril-web"

  Scenario: WebSocket connection
    Given the AiTril web server is running
    When I establish a WebSocket connection
    Then I should receive a connection confirmation
    And the connection should remain open
