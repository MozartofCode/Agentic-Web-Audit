"""'How to add this' steps for each Fix-it pack file, per detected platform."""

from __future__ import annotations

from typing import Optional

# Fix-it pack file id → steps. Used when no platform was detected or it has no override.
GENERIC: dict[str, list[str]] = {
    "llms_txt": [
        "Save the file as llms.txt.",
        "Upload it to the root of your site so it opens at https://yoursite.com/llms.txt.",
        "Open that URL in a browser to confirm it shows plain text, not your homepage.",
    ],
    "robots_txt": [
        "Lines starting with + are additions, lines starting with - are removals.",
        "Edit robots.txt at the root of your site (or your CMS's robots.txt setting).",
        "The commented-out training block is optional — uncomment it only if you want to opt "
        "out of AI model training. It does not affect AI search answers.",
    ],
    "json_ld": [
        "Replace every value marked TODO, and delete any block you don't need.",
        "Paste the <script> blocks into the <head> of your homepage (FAQPage: on the page "
        "that shows those questions).",
        "Check the result at https://validator.schema.org.",
    ],
    "meta_tags": [
        "Paste these tags inside the <head> of your homepage, replacing any existing tags "
        "with the same name or property.",
        "Keep the description true to what's visible on the page.",
    ],
}

PLATFORM_STEPS: dict[str, dict[str, list[str]]] = {
    "wordpress": {
        "llms_txt": [
            "Easiest: SEO plugins such as Yoast SEO or Rank Math can generate an llms.txt for "
            "you — or upload this file to your site root (the folder with wp-config.php) via "
            "your host's file manager or SFTP.",
            "Check https://yoursite.com/llms.txt opens as plain text.",
        ],
        "robots_txt": [
            "WordPress serves a virtual robots.txt. Edit it in Yoast SEO → Tools → File editor, "
            "or Rank Math → General Settings → Edit robots.txt.",
            "Apply the + lines and remove the - lines.",
        ],
        "json_ld": [
            "Yoast / Rank Math already output basic Organization schema — fill in the "
            "organization details in the plugin settings first.",
            "For the rest, use a header-code plugin (e.g. WPCode) to add the <script> blocks "
            "to the site header, replacing TODO values.",
        ],
        "meta_tags": [
            "Set the title and meta description in your SEO plugin's box under the homepage "
            "editor (Yoast: 'SEO title' and 'Meta description').",
            "Set the social image under the plugin's Social / Open Graph tab.",
        ],
    },
    "shopify": {
        "llms_txt": [
            "Shopify doesn't let you upload files to the site root. Upload llms.txt in "
            "Content → Files and copy its URL.",
            "Then add a redirect in Online Store → Navigation → URL redirects from /llms.txt "
            "to that file URL.",
        ],
        "robots_txt": [
            "In Online Store → Themes → … → Edit code, add a robots.txt.liquid template.",
            "Keep Shopify's default rules and add the + lines from this diff.",
        ],
        "json_ld": [
            "Most themes already output Product schema on product pages — only add what's "
            "missing.",
            "In Online Store → Themes → … → Edit code, paste the Organization/FAQ blocks into "
            "theme.liquid just before </head>.",
        ],
        "meta_tags": [
            "Online Store → Preferences: set the homepage title, meta description and social "
            "sharing image.",
        ],
    },
    "webflow": {
        "llms_txt": [
            "Check Site settings → SEO for an llms.txt upload option; if your plan doesn't "
            "have it, host the file elsewhere and add a 301 redirect from /llms.txt in "
            "Site settings → Publishing → 301 redirects.",
        ],
        "robots_txt": [
            "Site settings → SEO → Indexing → robots.txt: apply the changes, then publish.",
        ],
        "json_ld": [
            "Page settings → Custom code → Inside <head> tag: paste the <script> blocks, then "
            "publish. (Site-wide: Site settings → Custom code → Head code.)",
        ],
        "meta_tags": [
            "Page settings → SEO settings: title tag and meta description.",
            "Page settings → Open Graph settings: OG title, description and image.",
        ],
    },
    "wix": {
        "llms_txt": [
            "Wix doesn't allow arbitrary files at the site root. Check Settings → SEO for an "
            "llms.txt option; otherwise host the file and add a 301 redirect from /llms.txt in "
            "SEO → URL redirect manager.",
        ],
        "robots_txt": [
            "Dashboard → Marketing & SEO → SEO → Robots.txt editor: apply the changes.",
        ],
        "json_ld": [
            "Page SEO settings → Advanced SEO → Structured data markup: add each JSON block "
            "(paste only the JSON, without the <script> tags).",
        ],
        "meta_tags": [
            "Page SEO settings → Basics: title tag and meta description.",
            "Page SEO settings → Social share: OG image and text.",
        ],
    },
    "squarespace": {
        "llms_txt": [
            "Squarespace doesn't allow files at the site root. Upload llms.txt as a file "
            "(link editor → File), then add a URL mapping in Settings → Developer tools → URL "
            "mappings: /llms.txt -> <file URL> 301.",
        ],
        "robots_txt": [
            "Squarespace manages robots.txt for you. Under Settings → Crawlers, make sure "
            "'Block AI crawlers' / 'Block search engine crawlers' are turned off.",
        ],
        "json_ld": [
            "Settings → Developer tools → Code injection → Header: paste the <script> blocks "
            "(code injection needs a Business plan or higher).",
        ],
        "meta_tags": [
            "Pages → homepage ⚙ → SEO: SEO title and description.",
            "Pages → homepage ⚙ → Social image.",
        ],
    },
    "framer": {
        "llms_txt": [
            "Framer can't host files at the site root. Host llms.txt elsewhere and add a "
            "redirect from /llms.txt in Site settings → Redirects.",
        ],
        "robots_txt": [
            "Framer generates robots.txt. Check Site settings → General for indexing options, "
            "and use the + lines as a checklist.",
        ],
        "json_ld": [
            "Site settings → General → Custom code → End of <head> tag: paste the <script> "
            "blocks, then publish.",
        ],
        "meta_tags": [
            "Site settings → General (site-wide) or Page settings → SEO: title, description "
            "and social preview image.",
        ],
    },
    "nextjs": {
        "llms_txt": [
            "Save the file as public/llms.txt — Next.js serves it at /llms.txt.",
        ],
        "robots_txt": [
            "If you have public/robots.txt, edit it. With the App Router you may have "
            "app/robots.ts instead — add rules: [{ userAgent: [...answer bots], allow: '/' }].",
        ],
        "json_ld": [
            "In app/layout.tsx (or the page), render each block as "
            "<script type=\"application/ld+json\" dangerouslySetInnerHTML={{ __html: "
            "JSON.stringify(data) }} />.",
        ],
        "meta_tags": [
            "App Router: export const metadata = { title, description, alternates: "
            "{ canonical }, openGraph: { title, description, images } } in app/layout.tsx or "
            "app/page.tsx.",
            "Set <html lang=\"en\"> in app/layout.tsx.",
        ],
    },
}


def how_to(file_id: str, platform_id: Optional[str]) -> list[str]:
    """Install steps for one Fix-it pack file, tailored to the platform when known."""
    steps = PLATFORM_STEPS.get(platform_id or "", {}).get(file_id)
    return steps or GENERIC.get(file_id, [])
