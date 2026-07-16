<template>
  <div>
    <TopBar title="{{PAGE_TITLE}}" />
    <div class="page-shell{{PAGE_SHELL_EXTRA_CLASSES}}">
      {{BODY_SECTIONS}}
    </div>
    <TabBar />
    {{OVERLAY_SECTIONS}}
  </div>
</template>
