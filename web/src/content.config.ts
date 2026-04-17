import { defineCollection } from "astro:content";
import { glob } from "astro/loaders";
import { z } from "astro:schema";

const blog = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "../content/blog" }),
  schema: z.object({
    title: z.string(),
    author: z.string(),
    publication: z.string(),
    date: z.coerce.date(),
    tags: z.array(z.string()),
    summary: z.string(),
  }),
});

export const collections = { blog };
