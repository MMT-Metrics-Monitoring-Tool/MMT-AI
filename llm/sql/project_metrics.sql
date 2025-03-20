SELECT wr.week,
  SUM(wh.duration) AS 'duration',
  wr.meetings,
  mt.description,
  m.value
FROM projects p
  LEFT JOIN weeklyreports wr ON wr.project_id = p.id
  LEFT JOIN weeklyhours wh ON wh.weeklyreport_id = wr.id
  LEFT JOIN metrics m ON m.weeklyreport_id = wr.id
  INNER JOIN metrictypes mt ON mt.id = m.metrictype_id
WHERE p.id = 22
GROUP BY m.id;
