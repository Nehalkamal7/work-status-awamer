CREATE TABLE `whatsapp_updates` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`message_id` text NOT NULL,
	`project_code` text NOT NULL,
	`chat_name` text NOT NULL,
	`sender` text,
	`summary` text NOT NULL,
	`message_date` text NOT NULL,
	`created_at` text NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `whatsapp_updates_message_id_unique` ON `whatsapp_updates` (`message_id`);