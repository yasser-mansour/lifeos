package com.lifeos.app.ui.format

import com.google.gson.Gson

private val gson = Gson()

// Mirrors backend apps.people.models.RELATIONSHIP_CHOICES — kept as a small
// local copy the same way FOCUS_DOMAINS mirrors the study domain choices,
// since Android has no shared-with-backend enum mechanism. Expanded for
// Finance V2 (docs/FINANCE_V2.md) alongside Person AND Organization, which
// now share this exact vocabulary.
private val RELATIONSHIP_LABELS = mapOf(
    "client" to "Client", "prospect" to "Prospect", "service_provider" to "Service Provider",
    "supplier" to "Supplier", "employer_payer" to "Employer / Payer", "friend" to "Friend",
    "family" to "Family", "teacher" to "Teacher", "school" to "School", "bank" to "Bank",
    "landlord" to "Landlord", "platform" to "Platform", "partner" to "Partner",
    "collaborator" to "Collaborator", "contact" to "Contact", "other" to "Other",
)

/** "Client" / "Friend, Teacher" — the relationship-type chips a person's row
 * and detail both show (spec's People list mockup: "relationship label"). */
fun relationshipLabels(relationshipTypesJson: String): List<String> {
    val raw = runCatching { gson.fromJson(relationshipTypesJson, Array<String>::class.java)?.toList() }.getOrNull().orEmpty()
    return raw.map { RELATIONSHIP_LABELS[it] ?: it.replaceFirstChar { c -> c.uppercase() } }
}
