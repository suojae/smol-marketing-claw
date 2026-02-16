---
name: post
description: Post to SNS platforms (X/Twitter or Threads)
user_invocable: true
---

# /smol-claw:post

Post content to social media platforms.

## Arguments

- First argument: platform ("x" or "threads")
- Remaining arguments: the post text

Example: `/smol-claw:post x "Just shipped a new feature!""`

## Steps

1. Parse the first argument as the platform
2. Join remaining arguments as the post text
3. Based on platform:
   - "x" or "twitter": Call `smol_claw_post_x` with the text
   - "threads": Call `smol_claw_post_threads` with the text
4. Display the result (success/failure, post ID)
