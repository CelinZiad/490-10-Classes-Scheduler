-- Enum used in sequenceTerm and sequencePlan tables.

CREATE TYPE entry_terms AS ENUM ('winter', 'fall', 'summer');

-- public.building definition

-- Drop table

-- DROP TABLE public.building;

CREATE TABLE public.building (
	campus varchar NOT NULL,
	building varchar NOT NULL,
	buildingname varchar NULL,
	address varchar NULL,
	latitude varchar NULL,
	longitude varchar NULL,
	CONSTRAINT building_pk PRIMARY KEY (campus, building)
);


-- public."catalog" definition

-- Drop table

-- DROP TABLE public."catalog";

CREATE TABLE public."catalog" (
	id int4 NOT NULL,
	title varchar NULL,
	subject varchar NULL,
	"catalog" varchar NULL,
	career varchar NULL,
	classunit float4 NULL,
	prerequisites varchar NULL,
	crosslisted varchar NULL,
	CONSTRAINT catalog_pk PRIMARY KEY (id)
);


-- public.facultydept definition

-- Drop table

-- DROP TABLE public.facultydept;

CREATE TABLE public.facultydept (
	facultycode varchar NOT NULL,
	facultydescription varchar NOT NULL,
	departmentcode varchar NULL,
	departmentdescription varchar NULL,
	CONSTRAINT facultydept_pk PRIMARY KEY (facultycode, facultydescription)
);


-- public.labrooms definition

-- Drop table

-- DROP TABLE public.labrooms;

CREATE TABLE public.labrooms (
	campus varchar NULL,
	building varchar NULL,
	room varchar NULL,
	labroomid int4 NOT NULL,
	resources varchar NULL,
	CONSTRAINT labrooms_pk PRIMARY KEY (labroomid),
	CONSTRAINT labrooms_unique UNIQUE (campus, building, room)
);


-- public.scheduleterm definition

-- Drop table

-- DROP TABLE public.scheduleterm;

CREATE TABLE public.scheduleterm (
	subject varchar NOT NULL,
	"catalog" varchar NOT NULL,
	"section" varchar NOT NULL,
	componentcode varchar NULL,
	termcode int4 NOT NULL,
	classnumber int4 NOT NULL,
	"session" varchar NULL,
	buildingcode varchar NULL,
	room varchar NULL,
	instructionmodecode varchar NULL,
	locationcode varchar NULL,
	currentwaitlisttotal int4 NULL,
	waitlistcapacity int4 NULL,
	enrollmentcapacity int4 NULL,
	currentenrollment int4 NULL,
	departmentcode varchar NULL,
	facultycode varchar NULL,
	classstarttime time NULL,
	classendtime time NULL,
	classstartdate date NULL,
	classenddate date NULL,
	mondays bool NULL,
	tuesdays bool NULL,
	wednesdays bool NULL,
	thursdays bool NULL,
	fridays bool NULL,
	saturdays bool NULL,
	sundays bool NULL,
	CONSTRAINT scheduleterm_pk PRIMARY KEY (subject, catalog, section, termcode, classnumber)
);


-- public."section" definition

-- Drop table

-- DROP TABLE public."section";

CREATE TABLE public."section" (
	term int4 NOT NULL,
	"session" varchar NULL,
	overallenrollcapacity int4 NULL,
	overallenrollments int4 NULL,
	overallwaitlistcapacity int4 NULL,
	overallwaitlisttotal int4 NULL,
	subject varchar NOT NULL,
	"catalog" varchar NOT NULL,
	component varchar NULL,
	classnumber int4 NOT NULL,
	classenrollcapacity int4 NULL,
	classenrollments int4 NULL,
	classwaitlistcapacity int4 NULL,
	classwaitlisttotal int4 NULL,
	"section" varchar NOT NULL,
	CONSTRAINT section_pk PRIMARY KEY (term, subject, catalog, classnumber, section)
);


-- public.sessions definition

-- Drop table

-- DROP TABLE public.sessions;

CREATE TABLE public.sessions (
	career varchar NULL,
	termcode int4 NOT NULL,
	termdescription varchar NULL,
	sessioncode varchar NOT NULL,
	sessiondescription varchar NULL,
	sessionbegindate date NULL,
	sessionenddate date NULL,
	CONSTRAINT sessions_pk PRIMARY KEY (termcode, sessioncode)
);


-- public."user" definition

-- Drop table

-- DROP TABLE public."user";

CREATE TABLE public."user" (
	username varchar NOT NULL,
	"password" varchar NOT NULL,
	"name" varchar NULL,
	CONSTRAINT user_pk PRIMARY KEY (username)
);


-- public.sequenceplan definition

-- Drop table

-- DROP TABLE public.sequenceplan;

CREATE TABLE public.sequenceplan (
	planid int4 NOT NULL,
	planname varchar NOT NULL,
	"program" varchar NULL,
	entryterm public.entry_terms NOT NULL,
	"option" varchar NULL,
	durationyears int4 NULL,
	publishedon timestamp NULL,
	CONSTRAINT sequenceplan_pk PRIMARY KEY (planid),
	CONSTRAINT sequenceplan_unique UNIQUE (planname)
);


-- public.courselabs definition

-- Drop table

-- DROP TABLE public.courselabs;

CREATE TABLE public.courselabs (
	courseid int4 NOT NULL,
	labroomid int4 NULL,
	CONSTRAINT courselabs_labrooms_fk FOREIGN KEY (labroomid) REFERENCES public.labrooms(labroomid) ON DELETE SET NULL ON UPDATE SET NULL
);


-- public.studentschedulestudy definition

-- Drop table

-- DROP TABLE public.studentschedulestudy;

CREATE TABLE public.studentschedulestudy (
	studyid int4 NOT NULL,
	studyname varchar NULL,
	"owner" varchar NOT NULL,
	CONSTRAINT studentschedulestudy_pk PRIMARY KEY (studyid),
	CONSTRAINT studentschedulestudy_unique UNIQUE (studyname, owner),
	CONSTRAINT studentschedulestudy_user_fk FOREIGN KEY ("owner") REFERENCES public."user"(username) ON DELETE CASCADE ON UPDATE CASCADE
);


-- public.sequenceterm definition

-- Drop table

-- DROP TABLE public.sequenceterm;

CREATE TABLE public.sequenceterm (
	sequencetermid int4 NOT NULL,
	planid int4 NOT NULL,
	yearnumber int4 NOT NULL,
	season public.entry_terms NOT NULL,
	workterm bool DEFAULT false NOT NULL,
	notes varchar NULL,
	CONSTRAINT sequenceterm_pk PRIMARY KEY (sequencetermid),
	CONSTRAINT sequenceterm_unique UNIQUE (planid, yearnumber, season, workterm),
	CONSTRAINT sequenceterm_sequenceplan_fk FOREIGN KEY (planid) REFERENCES public.sequenceplan(planid) ON DELETE CASCADE ON UPDATE CASCADE
);


-- public.sequencecourse definition

-- Drop table

-- DROP TABLE public.sequencecourse;

CREATE TABLE public.sequencecourse (
	sequencetermid int4 NOT NULL,
	subject varchar NOT NULL,
	"catalog" varchar NOT NULL,
	"label" varchar NULL,
	iselective bool NOT NULL,
	CONSTRAINT sequencecourse_pk PRIMARY KEY (sequencetermid, subject, catalog),
	CONSTRAINT sequencecourse_sequenceterm_fk FOREIGN KEY (sequencetermid) REFERENCES public.sequenceterm(sequencetermid) ON DELETE CASCADE ON UPDATE CASCADE
);


-- public.studentschedule definition

-- Drop table

-- DROP TABLE public.studentschedule;

CREATE TABLE public.studentschedule (
	studentscheduleid int4 NOT NULL,
	schedulename varchar NULL,
	notes varchar NULL,
	studyid int4 NOT NULL,
	CONSTRAINT studentschedule_pk PRIMARY KEY (studentscheduleid),
	CONSTRAINT studentschedule_unique UNIQUE (schedulename, studyid),
	CONSTRAINT studentschedule_studentschedulestudy_fk FOREIGN KEY (studyid) REFERENCES public.studentschedulestudy(studyid) ON DELETE CASCADE ON UPDATE CASCADE
);


-- public.studentscheduleclass definition

-- Drop table

-- DROP TABLE public.studentscheduleclass;

CREATE TABLE public.studentscheduleclass (
	classentryid int4 NOT NULL,
	studentscheduleid int4 NOT NULL,
	classnumber int4 NOT NULL,
	CONSTRAINT studentscheduleclass_pk PRIMARY KEY (classentryid),
	CONSTRAINT studentscheduleclass_unique UNIQUE (studentscheduleid, classnumber),
	CONSTRAINT studentscheduleclass_studentschedule_fk FOREIGN KEY (studentscheduleid) REFERENCES public.studentschedule(studentscheduleid) ON DELETE CASCADE ON UPDATE CASCADE
);
