-- Event Scheduling & Resource Allocation System Database
DROP DATABASE IF EXISTS event_scheduler;
CREATE DATABASE event_scheduler;
USE event_scheduler;

CREATE TABLE resources (
    resource_id INT AUTO_INCREMENT PRIMARY KEY,
    resource_name VARCHAR(100) NOT NULL,
    resource_type ENUM('room', 'instructor', 'equipment') NOT NULL
);

CREATE TABLE events (
    event_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    description TEXT
);

CREATE TABLE event_resource_allocation (
    allocation_id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT,
    resource_id INT,
    FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
    FOREIGN KEY (resource_id) REFERENCES resources(resource_id),
    UNIQUE KEY unique_event_resource (event_id, resource_id)
);

-- Sample data
INSERT INTO resources (resource_name, resource_type) VALUES
('Conference Room A', 'room'),
('Training Room B', 'room'),
('John Doe', 'instructor'),
('Projector X', 'equipment');
