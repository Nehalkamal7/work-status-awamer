import {index,integer,sqliteTable,text} from "drizzle-orm/sqlite-core";
export const whatsappUpdates=sqliteTable("whatsapp_updates",{
  id:integer("id").primaryKey({autoIncrement:true}),messageId:text("message_id").notNull().unique(),projectCode:text("project_code").notNull(),chatName:text("chat_name").notNull(),sender:text("sender"),summary:text("summary").notNull(),messageDate:text("message_date").notNull(),createdAt:text("created_at").notNull()
},table=>[index("idx_whatsapp_updates_date").on(table.messageDate)]);
