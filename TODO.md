# TODO

- [x] Fix TemplateSyntaxError in `provider_profile_list.html` by removing dependency on non-existent `get_item` template filter.
- [x] Update `ProviderProfileListView.get_context_data` to attach `average_rating`, `review_count`, and `jobs_completed` to each `profiles` item.
- [x] Update `provider_profile_list.html` to read `profile.average_rating`, `profile.review_count`, `profile.jobs_completed`.
- [ ] Quick sanity check: ensure pages render without `get_item` usage.

