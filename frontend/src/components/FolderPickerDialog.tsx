import React, { useState, useCallback, useEffect } from 'react';
import { Folder, ChevronRight, ChevronDown, Loader2 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { filesystemAPI } from '@/services/api';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';

interface FolderPickerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (path: string) => void;
}

interface TreeNode {
  name: string;
  path: string;
  children: TreeNode[] | null;
  loaded: boolean;
}

const FolderPickerDialog: React.FC<FolderPickerDialogProps> = ({
  open,
  onOpenChange,
  onSelect,
}) => {
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [rootNode, setRootNode] = useState<TreeNode | null>(null);
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());

  const { data: rootData } = useQuery({
    queryKey: ['filesystem-root'],
    queryFn: () => filesystemAPI.getRoot(),
    staleTime: Infinity,
  });

  useEffect(() => {
    if (rootData?.data?.root) {
      setRootNode({
        name: rootData.data.root,
        path: rootData.data.root,
        children: null,
        loaded: false,
      });
    }
  }, [rootData]);

  const loadChildren = useCallback(
    async (path: string): Promise<TreeNode[]> => {
      const response = await filesystemAPI.getDirs(path);
      return response.data.dirs.map((dir: string) => ({
        name: dir,
        path: path.endsWith('/') ? path + dir : path + '/' + dir,
        children: null,
        loaded: false,
      }));
    },
    []
  );

  const toggleExpand = useCallback(
    async (node: TreeNode) => {
      if (expandedPaths.has(node.path)) {
        setExpandedPaths((prev) => {
          const next = new Set(prev);
          next.delete(node.path);
          return next;
        });
        return;
      }

      setExpandedPaths((prev) => new Set(prev).add(node.path));

      if (!node.loaded) {
        const children = await loadChildren(node.path);
        node.children = children;
        node.loaded = true;
        setRootNode({ ...rootNode! });
      }
    },
    [expandedPaths, loadChildren, rootNode]
  );

  const handleSelect = () => {
    if (selectedPath) {
      onSelect(selectedPath);
      onOpenChange(false);
    }
  };

  const renderNode = (node: TreeNode, depth: number): React.ReactNode => {
    const isExpanded = expandedPaths.has(node.path);
    const isSelected = selectedPath === node.path;
    const isLoading = isExpanded && !node.loaded;

    return (
      <div key={node.path}>
        <div
          className={`flex items-center gap-1 py-1 px-1 rounded cursor-pointer transition-colors
            ${isSelected ? 'bg-primary/20 text-primary' : 'hover:bg-accent'}`}
          style={{ paddingLeft: depth * 20 + 4 }}
          onClick={() => {
            setSelectedPath(node.path);
            toggleExpand(node);
          }}
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin shrink-0" />
          ) : isExpanded ? (
            <ChevronDown className="h-4 w-4 shrink-0" />
          ) : (
            <ChevronRight className="h-4 w-4 shrink-0" />
          )}
          <Folder className="h-4 w-4 shrink-0 text-yellow-500" />
          <span className="text-sm truncate ml-1">{node.name}</span>
        </div>
        {isExpanded &&
          node.children?.map((child) => renderNode(child, depth + 1))}
      </div>
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[70vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Selecionar Pasta</DialogTitle>
        </DialogHeader>
        <div className="flex-1 overflow-y-auto min-h-[300px] border rounded-lg p-2">
          {rootNode ? (
            renderNode(rootNode, 0)
          ) : (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button onClick={handleSelect} disabled={!selectedPath}>
            Selecionar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default FolderPickerDialog;
