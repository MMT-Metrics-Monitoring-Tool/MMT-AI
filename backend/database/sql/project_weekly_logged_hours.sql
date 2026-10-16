SELECT YEARWEEK(wh.date, 3) DIV 100 AS 'iso_year',
  YEARWEEK(wh.date, 3) MOD 100 AS 'iso_week',
  SUM(wh.duration) AS 'hours'
FROM members m
  INNER JOIN workinghours wh ON wh.member_id = m.id
WHERE m.project_id = %s
GROUP BY YEARWEEK(wh.date, 3)
ORDER BY YEARWEEK(wh.date, 3);
