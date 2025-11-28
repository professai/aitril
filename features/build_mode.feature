Feature: Build Mode - Multi-Phase Code Generation
  As a user
  I want to use build mode for code generation
  So that I can create code with consensus and review

  Background:
    Given the AiTril web server is running
    And I have a WebSocket connection

  Scenario: Complete build workflow
    When I send a build mode request with prompt "Create a hello world function"
    Then I should receive a "build_started" event
    And I should see the "planning" phase
    And I should see the "implementation" phase
    And I should see the "review" phase
    And I should see the "deployment" phase
    And I should receive deployment options
    And I should receive a "build_completed" event

  Scenario: Build phases execute in order
    When I send a build mode request with prompt "Create a simple test"
    Then the phases should execute in this order:
      | phase          |
      | planning       |
      | implementation |
      | review         |
      | deployment     |

  Scenario: Deployment options are presented
    When I send a build mode request with prompt "Create a test"
    And the build completes
    Then I should see these deployment options:
      | option | name                |
      | local  | Local File System   |
      | docker | Docker Container    |
      | github | GitHub Pages        |
      | ec2    | AWS EC2             |
      | skip   | Skip Deployment     |
