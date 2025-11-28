Feature: Deployment Selection
  As a user
  I want to select deployment targets after building code
  So that I can deploy my generated code

  Background:
    Given the AiTril web server is running
    And I have a WebSocket connection

  Scenario Outline: Select deployment target
    When I send a deployment selection for "<target>"
    Then I should receive a "deployment_started" event
    And the deployment name should be "<name>"
    And I should receive a "status_message" event
    And I should receive a "deployment_completed" event

    Examples:
      | target | name                |
      | local  | Local File System   |
      | docker | Docker Container    |
      | github | GitHub Pages        |
      | ec2    | AWS EC2             |
      | skip   | Skip Deployment     |

  Scenario: Skip deployment shows completion message
    When I send a deployment selection for "skip"
    Then the status message should contain "Build complete"
    And the status message should contain "ready to use"

  Scenario: Non-skip deployment shows coming soon
    When I send a deployment selection for "docker"
    Then the status message should contain "initiated"
    And the status message should contain "Implementation coming soon"
