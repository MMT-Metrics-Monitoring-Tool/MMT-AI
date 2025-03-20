SELECT r.description,
  r.impact,
  r.probability,
  r.severity,
  r.status,
  r.cause,
  r.mitigation,
  r.realizations,
  r.category
FROM projects p
  INNER JOIN risks r ON r.project_id = p.id
WHERE p.id = 22;
