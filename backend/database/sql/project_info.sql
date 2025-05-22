SELECT p.project_name,
  p.created_on,
  p.finished_date,
  CURDATE() AS 'current_date'
FROM projects p
WHERE p.id = %s;
