SELECT wr.year,
  wr.week,
  wr.meetings,
  (
    SELECT SUM(wh.duration)
    FROM weeklyhours wh
    WHERE wh.weeklyreport_id = wr.id
  ) AS 'reported_hours',
  mt.description,
  m.value
FROM weeklyreports wr
  INNER JOIN metrics m ON m.weeklyreport_id = wr.id
  INNER JOIN metrictypes mt ON mt.id = m.metrictype_id
WHERE wr.project_id = %s
ORDER BY wr.year, wr.week, mt.id;
