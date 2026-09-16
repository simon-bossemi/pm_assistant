CREATE TABLE `dependency_reviews` (
	`id` text PRIMARY KEY NOT NULL,
	`decision` text NOT NULL,
	`note` text NOT NULL,
	`updated_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `plan_snapshots` (
	`id` text PRIMARY KEY NOT NULL,
	`observed_at` text NOT NULL,
	`created_at` text NOT NULL,
	`source_modified_at` text NOT NULL,
	`name` text NOT NULL,
	`row_count` integer NOT NULL,
	`payload` text NOT NULL
);
