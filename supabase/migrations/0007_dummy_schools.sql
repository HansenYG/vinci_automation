-- Add more dummy school names for testing the chatbot school creation flow.
-- These are common Hong Kong / international school names that admins
-- might type when creating lessons.  Run AFTER 0006_rls_policies.sql.

insert into public.schools (school_id, school_name) values
('SCH-DM-SCH001', 'St. Mary's Canossian College'),
('SCH-DM-SCH002', 'Diocesan Boys'' School'),
('SCH-DM-SCH003', 'La Salle College'),
('SCH-DM-SCH004', 'Maryknoll Convent School'),
('SCH-DM-SCH005', 'King''s College'),
('SCH-DM-SCH006', 'Queen''s College'),
('SCH-DM-SCH007', 'Wah Yan College Hong Kong'),
('SCH-DM-SCH008', 'Wah Yan College Kowloon'),
('SCH-DM-SCH009', 'St. Paul''s Co-Educational College'),
('SCH-DM-SCH010', 'St. Paul''s Convent School'),
('SCH-DM-SCH011', 'Good Hope School'),
('SCH-DM-SCH012', 'Heep Yunn School'),
('SCH-DM-SCH013', 'St. Stephen''s College'),
('SCH-DM-SCH014', 'Canadian International School'),
('SCH-DM-SCH015', 'Hong Kong International School'),
('SCH-DM-SCH016', 'Australian International School'),
('SCH-DM-SCH017', 'Singapore International School'),
('SCH-DM-SCH018', 'English Schools Foundation (ESF)'),
('SCH-DM-SCH019', 'King George V School'),
('SCH-DM-SCH020', 'Sha Tin College'),
('SCH-DM-SCH021', 'South Island School'),
('SCH-DM-SCH022', 'West Island School'),
('SCH-DM-SCH023', 'Island School'),
('SCH-DM-SCH024', 'Discovery Bay International School'),
('SCH-DM-SCH025', 'Yew Chung International School'),
('SCH-DM-SCH026', 'Malvern College Hong Kong'),
('SCH-DM-SCH027', 'Harrow International School Hong Kong'),
('SCH-DM-SCH028', 'Shrewsbury International School'),
('SCH-DM-SCH029', 'Nord Anglia International School'),
('SCH-DM-SCH030', 'Victoria Shanghai Academy'),
('SCH-DM-SCH031', 'Tung Wah Group of Hospitals'),
('SCH-DM-SCH032', 'Pok Oi Hospital')
on conflict (school_id) do nothing;