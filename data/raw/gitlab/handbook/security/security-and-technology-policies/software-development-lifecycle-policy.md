---
title: "Software Development Lifecycle Policy"
controlled_document: true
tags:
  - security_policy
  - security_policy_caplscsi
---

{{< label name="Visibility: Non-Audit" color="#428BCA" >}}

## Purpose

Secure software development is critical to developing and maintaining a safe and trusted application. This policy outlines the general components of GitLab's software development lifecycle.

## Scope

This policy applies to anyone developing, reviewing, and merging code at GitLab in support of GitLab's production applications.

## Roles and responsibilities

| Role  | Responsibility |
|-----------|-----------|
| Security Governance | Responsible for creating and implementing this policy |
| Team members | Responsible for execution of the policy statements |

## Policy

In-scope development activities are performed in accordance with GitLab's [product development flow](/handbook/product-development/how-we-work/product-development-flow/).

Development activities are performed with security, confidentiality, and availability principles in mind.

Test data used throughout the development process is subject to GitLab's [Data Classification Standard](/handbook/security/policies_and_standards/data-classification-standard).

Every merge request must be reviewed and approved by a reviewer who neither authored the change nor directed an agent to author it, and who exercises independent judgment in the review.

GitLab must record the identity of each merge request's reviewers and approvers, including whether each identity belongs to a person or an agent. GitLab must retain these records as evidence.

When law, regulation, or contract requires explicit human approval, a person must approve the change. Examples include changes subject to SOX or FedRAMP controls.

## Standard

For further details, please review GitLab's [Software Development Lifecycle Standard](/handbook/security/policies_and_standards/software-development-lifecycle-standard).

## Exceptions

Exceptions to this procedure will be tracked as per the [Information Security Policy Exception Management Process](/handbook/security/controlled-document-procedure#exceptions).
