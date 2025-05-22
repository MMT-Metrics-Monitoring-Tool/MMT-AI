SELECT (
  SELECT SUM(m2.target_hours)
  FROM members m2
  WHERE m2.project_id = p.id
) AS 'target_hours',
  SUM(wh.duration) AS 'current_hours'
FROM projects p
  INNER JOIN members m ON m.project_id = p.id
  INNER JOIN workinghours wh ON wh.member_id = m.id
WHERE p.id = %s;
