CREATE DATABASE EventManagementSystem;
use EventManagementSystem;

CREATE TABLE USERS (
        user_id VARCHAR(100) PRIMARY KEY,
        dept VARCHAR(30),
        no_of_events INT
    );

CREATE TABLE LOGIN (
        user_id VARCHAR(100) PRIMARY KEY,
        password VARCHAR(50),
        account_type VARCHAR(10),
        FOREIGN KEY (user_id) REFERENCES USERS(user_id)
    );

CREATE TABLE DEPARTMENT (
        dept VARCHAR(30) PRIMARY KEY,
        default_fees INT,
        default_max_capacity INT
    );

CREATE TABLE EVENTS (
        event_id VARCHAR(10) PRIMARY KEY,
        date DATE,
        time TIME,
        dept VARCHAR(30),
        FOREIGN KEY (dept) REFERENCES DEPARTMENT(dept)
    );

CREATE TABLE HOST (
        event_id VARCHAR(10),
        user_id VARCHAR(100),
        PRIMARY KEY (event_id, user_id),
        FOREIGN KEY (event_id) REFERENCES EVENTS(event_id),
        FOREIGN KEY (user_id) REFERENCES USERS(user_id)
    );

-- USERS
INSERT INTO USERS VALUES
('U001', 'CSE', 2),
('U002', 'ECE', 1);

-- LOGIN
INSERT INTO LOGIN VALUES
('U001', 'pass123', 'student'),
('U002', 'secure456', 'admin');

-- DEPARTMENT
INSERT INTO DEPARTMENT VALUES
('CSE', 100, 50),
('ECE', 120, 30);

-- EVENTS
INSERT INTO EVENTS VALUES
('E101', '2025-06-01', '10:00:00', 'CSE'),
('E102', '2025-06-05', '11:00:00', 'CSE'),
('E103', '2025-06-10', '14:00:00', 'ECE');

-- HOST
INSERT INTO HOST VALUES
('E101', 'U001'),
('E102', 'U001'),
('E103', 'U002');

-- Views
CREATE VIEW DepartmentEvents AS
    SELECT 
        e.event_id,
        e.dept,
        e.date,
        e.time,
        d.default_fees,
        d.default_max_capacity
    FROM EVENTS e
    JOIN DEPARTMENT d ON e.dept = d.dept;

CREATE VIEW UserEventDetails AS
    SELECT 
        u.user_id,
        u.dept AS user_dept,
        e.event_id,
        e.date,
        e.time,
        e.dept AS event_dept,
        d.default_fees AS event_fees,
        d.default_max_capacity AS max_capacity
    FROM USERS u
    JOIN HOST h ON u.user_id = h.user_id
    JOIN EVENTS e ON h.event_id = e.event_id
    JOIN DEPARTMENT d ON e.dept = d.dept;

DELIMITER $$

    CREATE TRIGGER prevent_invalid_login_insert
    BEFORE INSERT ON LOGIN
    FOR EACH ROW
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM USERS WHERE user_id = NEW.user_id
        ) THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Cannot create login: user_id does not exist in USERS table.';
        END IF;
    END$$

    DELIMITER ;

 DELIMITER $$

    CREATE TRIGGER increment_event_count
    AFTER INSERT ON HOST
    FOR EACH ROW
    BEGIN
        UPDATE USERS
        SET no_of_events = no_of_events + 1
        WHERE user_id = NEW.user_id;
    END$$

    DELIMITER ;

-- Function
 DELIMITER $$

    CREATE FUNCTION getEventCount(u_id VARCHAR(100))
    RETURNS INT
    DETERMINISTIC
    BEGIN
        DECLARE count_events INT;

        SELECT COUNT(*) INTO count_events
        FROM HOST
        WHERE user_id = u_id;

        RETURN count_events;
    END$$

    DELIMITER ;

-- Procedure
DELIMITER $$

    CREATE PROCEDURE assignHost(IN e_id VARCHAR(10), IN u_id VARCHAR(100))
    BEGIN
        -- Check if the assignment already exists
        IF NOT EXISTS (
            SELECT * FROM HOST WHERE event_id = e_id AND user_id = u_id
        ) THEN
            INSERT INTO HOST (event_id, user_id) VALUES (e_id, u_id);

            UPDATE USERS
            SET no_of_events = no_of_events + 1
            WHERE user_id = u_id;
        END IF;
    END$$

    DELIMITER ;