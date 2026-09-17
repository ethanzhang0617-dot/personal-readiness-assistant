import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

// Minimal, safe renderer for the small Markdown subset the answer layer uses:
// paragraphs, "- " or "1. " lists and **bold**. Everything becomes React text
// nodes, so no HTML from an answer is ever parsed or injected.

type Block = { kind: "p" | "ul" | "ol"; items: string[] };

function parse(text: string): Block[] {
  const blocks: Block[] = [];
  let current: Block | null = null;

  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line) {
      current = null;
      continue;
    }
    const bullet = /^[-•]\s+(.*)$/.exec(line);
    const ordered = /^\d+[.)]\s+(.*)$/.exec(line);
    if (bullet) {
      if (current?.kind !== "ul") {
        current = { kind: "ul", items: [] };
        blocks.push(current);
      }
      current.items.push(bullet[1]);
      continue;
    }
    if (ordered) {
      if (current?.kind !== "ol") {
        current = { kind: "ol", items: [] };
        blocks.push(current);
      }
      current.items.push(ordered[1]);
      continue;
    }
    if (current?.kind === "p") {
      current.items.push(line);
    } else {
      current = { kind: "p", items: [line] };
      blocks.push(current);
    }
  }
  return blocks;
}

function inline(text: string, keyPrefix: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, index) =>
    part.length > 4 && part.startsWith("**") && part.endsWith("**") ? (
      <strong key={`${keyPrefix}-${index}`} className="font-semibold">
        {part.slice(2, -2)}
      </strong>
    ) : (
      <span key={`${keyPrefix}-${index}`}>{part}</span>
    ),
  );
}

export function RichText({ text, className }: { text: string; className?: string }) {
  const blocks = parse(text);
  return (
    <div className={cn("space-y-2 text-[0.9rem] leading-relaxed", className)}>
      {blocks.map((block, index) => {
        if (block.kind === "ul") {
          return (
            <ul key={index} className="ml-1 list-disc space-y-1 pl-4">
              {block.items.map((item, itemIndex) => (
                <li key={itemIndex}>{inline(item, `${index}-${itemIndex}`)}</li>
              ))}
            </ul>
          );
        }
        if (block.kind === "ol") {
          return (
            <ol key={index} className="ml-1 list-decimal space-y-1 pl-4">
              {block.items.map((item, itemIndex) => (
                <li key={itemIndex}>{inline(item, `${index}-${itemIndex}`)}</li>
              ))}
            </ol>
          );
        }
        return <p key={index}>{inline(block.items.join(" "), String(index))}</p>;
      })}
    </div>
  );
}
