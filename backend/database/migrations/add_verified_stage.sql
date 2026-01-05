-- Add 'verified' stage to offer_stage enum
ALTER TYPE offer_stage ADD VALUE IF NOT EXISTS 'verified';

-- Optional: Add verified_at timestamp to user_offer_progress table
ALTER TABLE user_offer_progress 
ADD COLUMN IF NOT EXISTS verified_at TIMESTAMP WITH TIME ZONE;





