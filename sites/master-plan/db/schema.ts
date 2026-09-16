import { sqliteTable,text,integer } from 'drizzle-orm/sqlite-core';
export const snapshots=sqliteTable('plan_snapshots',{
 id:text('id').primaryKey(),observedAt:text('observed_at').notNull(),createdAt:text('created_at').notNull(),sourceModifiedAt:text('source_modified_at').notNull(),name:text('name').notNull(),rowCount:integer('row_count').notNull(),summary:text('summary').notNull().default('{}'),payload:text('payload').notNull()
});
export const reviews=sqliteTable('dependency_reviews',{
 id:text('id').primaryKey(),decision:text('decision').notNull(),note:text('note').notNull(),updatedAt:text('updated_at').notNull()
});
