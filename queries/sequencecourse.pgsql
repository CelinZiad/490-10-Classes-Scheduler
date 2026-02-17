SELECT DISTINCT *
FROM public.sequencecourse 
JOIN public.sequenceterm 
  ON sequencecourse.sequencetermid = sequenceterm.sequencetermid 
JOIN public.sequenceplan 
  ON sequenceterm.planid = sequenceplan.planid
JOIN public.scheduleterm 
  ON sequencecourse.subject = scheduleterm.subject 
 AND sequencecourse.catalog = scheduleterm.catalog
LIMIT 1000;
