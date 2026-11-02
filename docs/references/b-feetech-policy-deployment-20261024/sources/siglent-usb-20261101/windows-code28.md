---
layout: Conceptual
title: CM_PROB_FAILED_INSTALL - Windows drivers | Microsoft Learn
canonicalUrl: https://learn.microsoft.com/en-us/windows-hardware/drivers/install/cm-prob-failed-install
Search.Product: eADQiWindows 10XVcnh
uhfHeaderId: MSDocsHeader-Windows
breadcrumb_path: /windows-hardware/drivers/breadcrumbs/toc.json
feedback_product_url: https://support.microsoft.com/help/4021566/windows-10-send-feedback-to-microsoft-with-feedback-hub-app
feedback_system: Standard
feedback_help_link_url: https://learn.microsoft.com/en-us/answers/tags/384/windows-hardware-performance
feedback_help_link_type: get-help-at-qna
ms.service: windows-hardware-driver-quality
author: robinharwood
ms.author: roharwoo
recommendations: true
ms.subservice: install
adobe-target: true
description: CM_PROB_FAILED_INSTALL
keywords:
- CM_PROB_FAILED_INSTALL
ms.date: 2020-02-28T00:00:00.0000000Z
ms.topic: error-reference
locale: en-us
document_id: a246b56c-e11e-f80d-92e6-e4d84e593ef7
document_version_independent_id: dfc9b9f7-2a8b-35f3-8328-67d9331ed2e6
updated_at: 2025-03-25T20:09:00.0000000Z
original_content_git_url: https://github.com/MicrosoftDocs/windows-driver-docs-pr/blob/live/windows-driver-docs-pr/install/cm-prob-failed-install.md
gitcommit: https://github.com/MicrosoftDocs/windows-driver-docs-pr/blob/cbec679f14ebb7b9cac07c8866dfb4a5af50be86/windows-driver-docs-pr/install/cm-prob-failed-install.md
git_commit_id: cbec679f14ebb7b9cac07c8866dfb4a5af50be86
site_name: Docs
depot_name: Win.drivers
page_type: conceptual
toc_rel: toc.json
pdf_url_template: https://learn.microsoft.com/pdfstore/en-us/Win.drivers/{branchName}{pdfName}
word_count: 335
asset_id: install/cm-prob-failed-install
moniker_range_name: 
monikers: []
item_type: Content
source_path: windows-driver-docs-pr/install/cm-prob-failed-install.md
cmProducts:
- https://authoring-docs-microsoft.poolparty.biz/devrel/bcbcbad5-4208-4783-8035-8481272c98b8
spProducts:
- https://authoring-docs-microsoft.poolparty.biz/devrel/43b2e5aa-8a6d-4de2-a252-692232e5edc8
platformId: a3c93dd8-09a9-9273-b2ca-5fcffde11696
---

# CM_PROB_FAILED_INSTALL - Windows drivers | Microsoft Learn

This Device Manager error message indicates that the device's drivers are not installed.

## Error Code

28

### Display Message

"The drivers for this device are not installed. (Code 28)"

### Recommended Resolution

Please visit the website of the company that manufactures the device and look for the most recent drivers for this device.

## For driver developers

The [**DEVPKEY\_Device\_ProblemStatus**](devpkey-device-problemstatus) property on the device should indicate the failure code.

### 0xC0000490 - STATUS\_PNP\_NO\_COMPAT\_DRIVERS

PnP could not find a compatible driver for the device. This failure is often referred to as a DNF (driver not found) problem.

Examine the hardware IDs and compatible IDs of the device in question and compare to the hardware ID(s) that the INF specifies under the [**Models sections**](inf-models-section). Also make sure that the **TargetOSVersion** part of the Models section name applies to the architecture and OS version you are running on.

### 0xC0000491 - STATUS\_PNP\_DRIVER\_PACKAGE\_NOT\_FOUND

This code indicates a missing driver package dependency.

Specifically, the INF that matched on the device uses **Include** entries in the [INF DDInstall section](inf-ddinstall-section) to specify a Microsoft-supplied INF that is not present in this version of Windows.

### 0xC0000492 - STATUS\_PNP\_DRIVER\_CONFIGURATION\_NOT\_FOUND

This code also indicates a missing driver package dependency.

In this case, the INF that matched on the device uses **Needs** entries in the [INF DDInstall section](inf-ddinstall-section) to specify a section that does not exist in any Microsoft-supplied INF referenced by an **Include** directive.

### 0xC0000494 - STATUS\_PNP\_FUNCTION\_DRIVER\_REQUIRED

This failure occurs when the INF does not specify an associated function driver service.

Verify that either:

1. The INF file for the device being installed contains an [**AddService directive**](inf-addservice-directive) that sets an associated service or function driver using the flag SPSVCINST\_ASSOCSERVICE (0x00000002).
2. The INF file specifies **Include** or **Needs** entries in a [INF DDInstall Section](inf-ddinstall-section) that reference a system-supplied driver that in turn sets an associated service on the device.

### Upgrade to Windows 10

Before upgrade, the device has a driver and is working fine. After upgrade, it shows Code 28. This is frequently caused by the driver package being excluded from the migration.