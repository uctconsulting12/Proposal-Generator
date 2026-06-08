import { useEffect, useRef, useState } from "react";
import {
  Box,
  Button,
  ButtonGroup,
  Popper,
  Grow,
  Paper,
  ClickAwayListener,
  MenuList,
  MenuItem,
  ListItemText,
  Typography,
  Divider,
  Tooltip,
  Chip,
  alpha,
} from "@mui/material";
import PictureAsPdfOutlinedIcon from "@mui/icons-material/PictureAsPdfOutlined";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import CheckIcon from "@mui/icons-material/Check";
import { templatesApi } from "../../api/templates.js";
import { useProfile } from "../../contexts/ProfileContext.jsx";

/**
 * Split-button: primary action exports using the user's default template;
 * the chevron opens a menu to pick a different template for this one export.
 */
export default function ExportMenu({ onExport, disabled }) {
  const { profile } = useProfile();
  const [open, setOpen] = useState(false);
  const [templates, setTemplates] = useState([]);
  const anchorRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    templatesApi
      .list()
      .then((data) => !cancelled && setTemplates(data.templates || []))
      .catch(() => {
        /* keep silent — the default-export button still works */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const defaultId = profile.template_id || "modern";
  const defaultName =
    templates.find((t) => t.id === defaultId)?.name || "default template";

  const exportWith = (templateId) => {
    setOpen(false);
    onExport({ template: templateId });
  };

  return (
    <>
      <ButtonGroup
        ref={anchorRef}
        size="small"
        variant="outlined"
        disabled={disabled}
        aria-label="Export proposal as PDF"
      >
        <Tooltip title={`Export using ${defaultName}`}>
          <Button
            startIcon={<PictureAsPdfOutlinedIcon />}
            onClick={() => onExport({})}
          >
            Export PDF
          </Button>
        </Tooltip>
        <Tooltip title="Pick a different template">
          <Button
            size="small"
            onClick={() => setOpen((o) => !o)}
            sx={{ minWidth: 28, px: 0.5 }}
            aria-controls={open ? "export-menu" : undefined}
            aria-haspopup="menu"
          >
            <ArrowDropDownIcon fontSize="small" />
          </Button>
        </Tooltip>
      </ButtonGroup>

      <Popper
        open={open}
        anchorEl={anchorRef.current}
        transition
        disablePortal
        placement="bottom-end"
        sx={{ zIndex: (t) => t.zIndex.modal }}
      >
        {({ TransitionProps }) => (
          <Grow {...TransitionProps} style={{ transformOrigin: "right top" }}>
            <Paper
              elevation={6}
              sx={{
                mt: 0.5,
                minWidth: 260,
                borderRadius: 2,
                border: 1,
                borderColor: "divider",
              }}
            >
              <ClickAwayListener onClickAway={() => setOpen(false)}>
                <Box>
                  <Box sx={{ px: 2, py: 1.25 }}>
                    <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700, letterSpacing: "0.06em" }}>
                      EXPORT WITH TEMPLATE
                    </Typography>
                  </Box>
                  <Divider />
                  <MenuList id="export-menu" autoFocusItem={open} dense>
                    {templates.length === 0 ? (
                      <MenuItem disabled>
                        <ListItemText primary="No templates available" />
                      </MenuItem>
                    ) : (
                      templates.map((t) => {
                        const isDefault = t.id === defaultId;
                        return (
                          <MenuItem
                            key={t.id}
                            onClick={() => exportWith(t.id)}
                            sx={{
                              py: 1,
                              "&:hover": {
                                bgcolor: (theme) =>
                                  alpha(theme.palette.primary.main, 0.06),
                              },
                            }}
                          >
                            <ListItemText
                              primary={
                                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                                  <Typography sx={{ fontWeight: 700 }}>
                                    {t.name}
                                  </Typography>
                                  {isDefault && (
                                    <Chip
                                      label="default"
                                      size="small"
                                      color="primary"
                                      variant="outlined"
                                      sx={{ height: 18, fontSize: "0.6rem" }}
                                    />
                                  )}
                                </Box>
                              }
                              secondary={
                                <Typography variant="caption" color="text.secondary">
                                  {t.tagline}
                                </Typography>
                              }
                            />
                            {isDefault && (
                              <CheckIcon
                                fontSize="small"
                                color="primary"
                                sx={{ ml: 1 }}
                              />
                            )}
                          </MenuItem>
                        );
                      })
                    )}
                  </MenuList>
                </Box>
              </ClickAwayListener>
            </Paper>
          </Grow>
        )}
      </Popper>
    </>
  );
}
